import time
from typing import Dict, List

import numpy as np
from colorama import Fore
from fastapi import WebSocket

from mock.sdk.types import API_Pipe, API_Proc, ProcType, PipeActionType, PipeExecutionStatus
from .process_controller import ProcessorController
from .processor_instance import ProcessorInstance
from .. import NodeClient
from ... import API_Pipe_Control_Message, API_Proc_Message, ProcMessageType, QStatus, ProcUtilizationEntry, MemQueue


class PipeController:
    def __init__(self, node_client: NodeClient, node_proc: API_Proc):
        self.node_client = node_client
        self.processors: Dict[str, ProcessorController] = {}
        self.queues: Dict[str, MemQueue] = {}
        self.utilization_log: Dict[str, List[ProcUtilizationEntry]] = {}
        self.utilization_log_size = 50
        self._q_usage_log: Dict[str, List[QStatus]] = {}
        self._q_usage_log_size = 50
        self.node_proc = node_proc
        self.status: PipeExecutionStatus = PipeExecutionStatus.INIT
        self.name = None

    def log_processor_utilization(self, utilization: ProcUtilizationEntry):
        proc_name = utilization.proc.name
        if proc_name not in self.utilization_log:
            self.utilization_log[proc_name] = []
        log = self.utilization_log[proc_name]
        log.append(utilization)
        while len(log) > self.utilization_log_size:
            del log[0]

    def log_node_utilization(self):
        self.log_q_usage()

    async def connect_proc(self, proc_name: str, websocket: WebSocket):
        if proc_name not in self.processors:
            return
        p: ProcessorController = self.processors[proc_name]
        await p.connect_proc(websocket)

    async def disconnect_proc(self, proc_name: str):
        if proc_name not in self.processors:
            return
        p: ProcessorController = self.processors[proc_name]
        await p.disconnect_proc()

    def process_control_message(self, pipe_control_msg: API_Pipe_Control_Message):
        if pipe_control_msg.action == PipeActionType.START:
            self.start()

    def process_pipe_message(self, proc_msg: API_Proc_Message):
        if proc_msg.type == ProcMessageType.PIPE_CONTROL:
            pipe_control_msg = API_Pipe_Control_Message.parse_obj(proc_msg)
            self.process_control_message(pipe_control_msg)

    def process_message(self, proc_msg: API_Proc_Message):
        try:
            if proc_msg.scope == ProcType.PIPELINE:
                self.process_pipe_message(proc_msg)
            if proc_msg.scope == ProcType.PROCESSOR:
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
            status = QStatus(q_id=q.qid, pending=q.pending_counter, time=current_time)
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
        return self.status == PipeExecutionStatus.RUNNING

    def start(self):
        if self.status == PipeExecutionStatus.INIT:
            raise AssertionError("Cant start an empty pipe")
        launched = 0
        for proc_name in self.processors:
            p: ProcessorController = self.processors[proc_name]
            if not p.executable:
                continue
            launched += 1
            p.launch_instance()
        self.status = PipeExecutionStatus.RUNNING
        print(f"Started {launched} processors")
        # self.send_pipe_status(PipeExecutionStatus.RUNNING)

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

    # def send_pipe_status(self, status: PipeExecutionStatus):
    #     status_message = API_Pipe_Status_Message(sender=self.api_def, type=ProcMessageType.PIPE_STATUS,
    #                                              dest=server_proc_def, status=status, scope=ProcType.SERVER,
    #                                              pipe_name=self.name)
    #     self.node_client.send_message(status_message)

    def log_pipe_utilization(self):
        for proc_name in self.processors:
            p = self.processors[proc_name]
            current_time = time.time() * 1000  # ms
            utilization = ProcUtilizationEntry(cpu=p.cpu, memory=p.memory, time=current_time, proc=p.proc)
            self.log_processor_utilization(utilization)

    def get_processor_queues(self, proc_name: str):
        proc_queues = []
        for qid in self.queues:
            queue = self.queues[qid]
            if queue.to_p == proc_name or queue.from_p == proc_name:
                proc_queues.append(queue)
        return proc_queues

    def load(self, pipe: API_Pipe):
        self.processors: Dict[str, ProcessorController] = {}
        self.queues: Dict[str, MemQueue] = {}
        for qid in pipe.queues:
            queue = pipe.queues[qid]
            self.queues[qid] = MemQueue(queue)
        for proc_name in pipe.processors:
            proc = pipe.processors[proc_name]
            proc_queues = self.get_processor_queues(proc_name)
            self.processors[proc_name] = ProcessorController(proc, proc_queues)
        self.status = PipeExecutionStatus.READY
        self.name = pipe.name

    def handle_control_msg(self, control_msg: API_Pipe_Control_Message):
        if control_msg.action == PipeActionType.START:
            return self.start()

    def remove_instance(self, instance: ProcessorInstance):
        p = self.processors[instance.name]
        p.instances.remove(instance)

    def handle_instance_exit(self, instance: ProcessorInstance):
        p = self.processors[instance.name]

        if instance.exit_code == 0:
            print(f"{instance.name}({instance.instance_id}) >> ************Completed**************")
            p.on_complete(False)
            self.remove_instance(instance)
        else:
            print(f"{instance.name}({instance.instance_id}) >> >>>>>>Completed with errors<<<<<<<<")
            p.on_complete(True)
        return

    def cleanup(self):
        self.status = PipeExecutionStatus.COMPLETED

    @property
    def api_def(self):
        return API_Proc(name=self.name, type=ProcType.PIPELINE_CONTROLLER)
