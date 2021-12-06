import asyncio
import time
from typing import Dict, List, Union

import numpy as np
from colorama import Fore
from fastapi import WebSocket

from ... import types, entities
from .process_controller import ProcessorController, ProcessorInstance
from ..client import NodeClient
from ...types import PipeExecutionStatus


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
        self.connections: List[WebSocket] = []
        self.pipe: Union[types.APIPipe, None] = None

    async def connect_pipe(self, websocket: WebSocket):
        await websocket.accept()
        msg = types.APIPipeStatusMessage(dest=self.name,
                                         type=types.UPipeMessageType.PIPE_STATUS,
                                         sender=self.api_def.id,
                                         status=self.status,
                                         pipe_name=self.name,
                                         scope=types.UPipeEntityType.PIPELINE)
        await websocket.send_json(msg.dict())
        self.connections.append(websocket)

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
                await p.connect_proc(websocket)
                return
        available_processors = ', '.join([key for key in self.processors.keys()])
        print("Instance launch error: {!r}. available: {}".format(pid, available_processors))
        raise BrokenPipeError(f"Can not connect process pid={pid}")

    async def disconnect_proc(self, proc_name: str):
        if proc_name not in self.processors:
            return
        p: ProcessorController = self.processors[proc_name]
        await p.disconnect_proc()

    def process_control_message(self, pipe_control_msg: types.APIPipeControlMessage):
        if pipe_control_msg.action == types.PipeActionType.START:
            self.start()
        if pipe_control_msg.action == types.PipeActionType.PAUSE:
            self.pause()

    def process_pipe_message(self, proc_msg: types.UPipeMessage):
        if proc_msg.type == types.UPipeMessageType.PIPE_CONTROL:
            pipe_control_msg = types.APIPipeControlMessage.parse_obj(proc_msg)
            self.process_control_message(pipe_control_msg)

    def process_message(self, proc_msg: types.UPipeMessage):
        try:
            if proc_msg.scope == types.UPipeEntityType.PIPELINE:
                self.process_pipe_message(proc_msg)
            if proc_msg.scope == types.UPipeEntityType.PROCESSOR:
                if proc_msg.dest not in self.processors:
                    return
                self.processors[proc_msg.dest].process_message(proc_msg)
        except Exception as e:
            print(f"Error on pipe message : {str(e)}")

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
        print(f"Started {launched} processors")
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

    async def set_pipe_status(self, status: PipeExecutionStatus):
        self.status = status
        msg = types.APIPipeStatusMessage(dest=self.name,
                                         type=types.UPipeMessageType.PIPE_STATUS,
                                         sender=self.api_def.id,
                                         status=status,
                                         pipe_name=self.name,
                                         scope=types.UPipeEntityType.PIPELINE)
        for connection in self.connections:
            await connection.send_json(msg.dict())

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

    def remove_instance(self, instance: ProcessorInstance):
        p = self.processors[instance.proc_id]
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
