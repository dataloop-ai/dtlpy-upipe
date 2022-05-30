import asyncio
import time
from typing import Dict, List, Union

import numpy as np
from colorama import Fore
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from .node_utils import WebsocketHandler
from ... import types, entities
from .processor_controller import ProcessorController, ProcessorInstance
from ...types import PipeExecutionStatus, APIProcessor, APIQueue


class PipeController:
    def __init__(self, node_proc: types.UPipeEntity):
        self.processors: Dict[str, ProcessorController] = {}
        self.queues: Dict[str, entities.MemQueue] = {}
        self.utilization_log: Dict[str, List[types.ProcUtilizationEntry]] = {}
        self.utilization_log_size = 50
        self._q_usage_log: Dict[str, List[types.QStatus]] = {}
        self._q_usage_log_size = 50
        self.node_proc = node_proc
        self.status: types.PipeExecutionStatus = types.PipeExecutionStatus.INIT
        self.name = None
        self.connections: List[WebsocketHandler] = []
        self.pipe: Union[types.APIPipe, None] = None
        self.msg_counter = 0

    def get_proc_queues(self, proc_id: str) -> List[APIQueue]:
        queues: List[APIQueue] = []
        for qid in self.queues:
            queue = self.queues[qid]
            if queue.from_p == proc_id or queue.to_p == proc_id:
                api_q: APIQueue = queue.queue_def
                queues.append(api_q)
        return queues

    async def connect_pipe(self, websocket: WebSocket):
        handler = WebsocketHandler(f"pipe:{self.name}", websocket, self.process_message)
        await handler.init()
        self.connections.append(handler)
        messages = []
        msg = types.APIPipeStatusMessage(dest=self.name,
                                         type=types.UPipeMessageType.PIPE_STATUS,
                                         sender=self.api_def.id,
                                         status=self.status,
                                         pipe_name=self.name,
                                         scope=types.UPipeEntityType.PIPELINE)
        messages.append(msg)
        queues = self.get_proc_queues(self.pipe.root.id)
        q_dict = {}
        for q in queues:
            q_dict[q.id] = q
        queues_def = types.APIProcQueues(proc_id=self.pipe.root.id, queues=q_dict)
        q_update_msg = types.UPipeMessage(dest=self.pipe.root.id,
                                          sender=self.pipe.root.id,
                                          type=types.UPipeMessageType.Q_UPDATE,
                                          body=queues_def,
                                          scope=types.UPipeEntityType.PROCESSOR)
        messages.append(q_update_msg)
        await handler.send(messages)
        try:
            await handler.monitor()
        except WebSocketDisconnect:
            self.connections.remove(handler)

    def get_instance_by_pid(self, pid: int):
        launched = []
        for proc_id in self.processors:
            processor: ProcessorController = self.processors[proc_id]
            for instance in processor.instances:
                if instance.pid == pid or instance.is_child_process(pid):
                    return instance
        return None

    def get_processors_by_name(self, name: str):
        procs = []
        for proc_id in self.processors:
            processor: ProcessorController = self.processors[proc_id]
            if processor.name == name:
                procs.append(processor)
        return procs

    def log_processor_utilization(self, utilization: types.ProcUtilizationEntry):
        proc_name = utilization.proc.name
        if proc_name not in self.utilization_log:
            self.utilization_log[proc_name] = []
        log = self.utilization_log[proc_name]
        log.append(utilization)
        while len(log) > self.utilization_log_size:
            del log[0]

    def log_node_utilization(self):
        self.log_q_usage()

    async def connect_proc(self, pid: int, websocket: WebSocket):
        for proc_name in self.processors:
            p: ProcessorController = self.processors[proc_name]
            if p.is_my_process(pid):
                await p.connect_proc(pid, websocket)
                return
        available_processors = ', '.join([key for key in self.processors.keys()])
        print("Instance launch error: {!r}. available: {}".format(pid, available_processors))
        raise BrokenPipeError(f"Can not connect process pid={pid}")

    async def disconnect_proc(self, proc_name: str):
        if proc_name not in self.processors:
            return
        p: ProcessorController = self.processors[proc_name]
        await p.disconnect_proc()

    def process_control_message(self, pipe_control_msg: Union[types.APIPipeControlMessage, types.UPipeMessage]):
        if pipe_control_msg.action == types.PipeActionType.START:
            self.start()
        if pipe_control_msg.action == types.PipeActionType.PAUSE:
            self.pause()

    def process_message(self, pipe_msg: types.UPipeMessage):
        if pipe_msg.type == types.UPipeMessageType.PIPE_CONTROL:
            self.process_control_message(pipe_msg)

    def log_q_usage(self):
        current_time = time.time() * 1000  # ms
        for qid in self.queues:
            log = self._q_usage_log[qid]
            q = self.queues[qid]
            status = types.QStatus(q_id=q.qid, pending=q.pending_counter, time=current_time)
            log.append(status)
            while len(log) > self._q_usage_log_size:
                del log[0]

    def pending_counter(self, qid: str):
        log = self._q_usage_log[qid]
        pending = 0
        pending += int(np.mean([d.pending for d in log]))
        return pending

    def scale_up(self):
        processor_to_scale: ProcessorController = self.get_processor_to_scale_up()
        print(Fore.BLUE + f"scaling up:{processor_to_scale.name}")
        processor_to_scale.launch_instance()

    def scale_down(self):
        processor_to_scale: ProcessorController = self.get_processor_to_scale_down()
        print(Fore.BLUE + f"scaling down:{processor_to_scale.name}")
        processor_to_scale.scale_down()

    def get_processor_to_scale_up(self):
        max_pending = None
        processor_to_scale = None
        for proc_name in self.processors:
            p = self.processors[proc_name]
            if p.available_instances == 0:
                continue
            if max_pending is None or p.pending > max_pending:
                max_pending = p.pending
                processor_to_scale = proc_name
        return self.processors[processor_to_scale]

    @property
    def running(self):
        return self.status == types.PipeExecutionStatus.RUNNING

    def start(self):
        if self.status == types.PipeExecutionStatus.INIT:
            raise AssertionError("Cant start an empty pipe")
        launched = 0
        for proc_name in self.processors:
            p: ProcessorController = self.processors[proc_name]
            if not p.executable:
                continue
            launched += 1
            p.launch_instance()
        multi = ""
        if launched > 1:
            multi = 's'
        print(f"Started {launched} processor{multi}")
        loop = asyncio.get_event_loop()
        loop.create_task(self.set_pipe_status(PipeExecutionStatus.RUNNING))

    def pause(self):
        if self.status != types.PipeExecutionStatus.RUNNING:
            raise AssertionError("Cant pause an idle pipe")
        for proc_name in self.processors:
            p: ProcessorController = self.processors[proc_name]
            p.pause()
        loop = asyncio.get_event_loop()
        loop.create_task(self.set_pipe_status(PipeExecutionStatus.PAUSED))

    def request_termination(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.set_pipe_status(PipeExecutionStatus.PENDING_TERMINATION))
        self.terminate_next_processor()

    def terminate_next_processor(self):
        termination_list: List[APIProcessor] = self.pipe.drain_list()
        for proc_def in termination_list:
            processor: ProcessorController = self.processors[proc_def.id]
            if processor.running_instances_num == 0:
                continue
            processor.request_termination()
            break
        if self.running_processors_num == 0:
            loop = asyncio.get_event_loop()
            loop.create_task(self.set_pipe_status(PipeExecutionStatus.COMPLETED))

    def notify_termination(self, pid: int, proc: types.UPipeEntity):
        if proc.id in self.processors:
            self.processors[proc.id].notify_termination(pid)
        if self.pending_termination:
            self.terminate_next_processor()

    async def set_pipe_status(self, status: PipeExecutionStatus):
        self.status = status
        await self._sync_status()

    async def _sync_status(self):
        msg = types.APIPipeStatusMessage(dest=self.name,
                                         type=types.UPipeMessageType.PIPE_STATUS,
                                         sender=self.api_def.id,
                                         status=self.status,
                                         pipe_name=self.name,
                                         scope=types.UPipeEntityType.PIPELINE)
        for connection in self.connections:
            await connection.send(msg)

    @property
    def pending_termination(self):
        return self.status == PipeExecutionStatus.PENDING_TERMINATION

    @property
    def running_processors(self):
        return [self.processors[i] for i in self.processors if self.processors[i].running_instances_num > 0]

    @property
    def running_processors_num(self):
        return len(self.running_processors)

    @property
    def scaled_to_maxed(self):
        scale_limit_reached = True
        for proc_name in self.processors:
            p = self.processors[proc_name]
            if p.available_instances > 0:
                scale_limit_reached = False
                break
        return scale_limit_reached

    @property
    def is_scaled(self):
        for proc_name in self.processors:
            p = self.processors[proc_name]
            if p.instances_number > 1:
                return True
        return False

    @property
    def is_scaling(self):
        for proc_name in self.processors:
            p = self.processors[proc_name]
            if p.is_scaling:
                return True
        return False

    def get_processor_to_scale_down(self) -> ProcessorController:
        max_gap = None
        processor_to_scale_down = None
        for proc_name in self.processors:
            p = self.processors[proc_name]
            gap = p.proc.settings.autoscale - p.instances_number
            if max_gap is None or gap > max_gap:
                max_gap = gap
                processor_to_scale_down = proc_name
        return self.processors[processor_to_scale_down]

    def log_pipe_utilization(self):
        for proc_name in self.processors:
            p = self.processors[proc_name]
            current_time = time.time() * 1000  # ms
            utilization = types.ProcUtilizationEntry(cpu=p.cpu, memory=p.memory, time=current_time, proc=p.proc)
            self.log_processor_utilization(utilization)

    def get_processor_queues(self, proc_name: str):
        proc_queues = []
        for qid in self.queues:
            queue = self.queues[qid]
            if queue.to_p == proc_name or queue.from_p == proc_name:
                proc_queues.append(queue)
        return proc_queues

    def load(self, pipe: types.APIPipe):
        self.processors: Dict[str, ProcessorController] = {}
        self.queues: Dict[str, entities.MemQueue] = {}
        for qid in pipe.queues:
            queue = pipe.queues[qid]
            self.queues[qid] = entities.MemQueue(queue)
        self.queues[pipe.sink.id] = entities.MemQueue(pipe.sink)
        for proc_name in pipe.processors:
            proc = pipe.processors[proc_name]
            proc_queues = self.get_processor_queues(proc_name)
            self.processors[proc_name] = ProcessorController(proc, proc_queues)
        self.status = types.PipeExecutionStatus.READY
        self.name = pipe.name
        self.pipe = pipe

    def handle_control_msg(self, control_msg: types.APIPipeControlMessage):
        if control_msg.action == types.PipeActionType.START:
            return self.start()
        if control_msg.action == types.PipeActionType.TERMINATE:
            return self.request_termination()

    def remove_instance(self, instance: ProcessorInstance):
        p = self.processors[instance.proc.id]
        p.instances.remove(instance)

    def handle_instance_exit(self, instance: ProcessorInstance):
        p = self.processors[instance.proc_id]
        if instance.exit_code == 0:
            print(f"{instance.proc_id}({instance.pid}) >> ************Completed**************")
            p.on_complete(False)
            self.remove_instance(instance)
        else:
            print(f"{instance.proc_id}({instance.pid}) >> >>>>>>Completed with errors<<<<<<<<")
            p.on_complete(True)
        return

    def cleanup(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.set_pipe_status(PipeExecutionStatus.COMPLETED))

    @property
    def api_def(self):
        return types.UPipeEntity(name=self.name,
                                 id=self.name,
                                 type=types.UPipeEntityType.PIPELINE_CONTROLLER)
