import asyncio
import importlib
import inspect
import multiprocessing
import pathlib
import subprocess
import sys
import types
from enum import IntEnum
from multiprocessing.queues import Queue
from typing import List, Union

from fastapi import WebSocket

from ... import entities, utils
from ... import types as up_types
from .process_instance import InstanceType, ProcessorInstance, InstanceState

# This is a Queue that behaves like stdout
from ...types.performance import ProcessorPerformanceStats


class StdoutQueue(Queue):
    def __init__(self, *args, **kwargs):
        ctx = multiprocessing.get_context()
        super(StdoutQueue, self).__init__(*args, **kwargs, ctx=ctx)

    def write(self, msg):
        self.put(msg)

    @staticmethod
    def flush():
        sys.__stdout__.flush()


def launch_module(mode_name, mod_path, function_name, proc_stdout):
    old_stdout = sys.stdout
    sys.stdout = proc_stdout
    loader = importlib.machinery.SourceFileLoader(mode_name, mod_path)
    mod = types.ModuleType(loader.name)
    loader.exec_module(mod)
    f = getattr(mod, function_name)
    if inspect.iscoroutinefunction(f):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(f())
        # noinspection GrazieInspection
        loop.run_until_complete(asyncio.sleep(3))  # some time for things to cleanup like connections
        loop.close()
    else:
        f()
    return True


class ProcessType(IntEnum):
    MAIN = 1  # the process started the whole thing, usually pipeline script
    NODE_LOCAL_SERVER = 2  # the node server
    PROCESSOR = 3  # a launched processor


class ProcessorController:
    ALIVE_POINTER = 0  # size 1
    LAST_INSTANCE_ID_POINTER = 1  # size 4

    def __init__(self, proc: up_types.APIProcessor, queues: [entities.MemQueue]):
        self.proc: up_types.APIProcessor = proc
        self._instances: List[ProcessorInstance] = []
        self._interpreter_path = sys.executable
        self.status: up_types.ProcessorExecutionStatus = up_types.ProcessorExecutionStatus.INIT
        self._queues: [entities.MemQueue] = queues
        processor_memory_name = f"processor_control:{self.name}"
        size = entities.Processor.SHARED_MEM_SIZE
        self._control_mem = utils.SharedMemoryBuffer(name=processor_memory_name,
                                                     size=size,
                                                     mode=utils.MEMORY_ALLOCATION_MODE.CREATE_ONLY)

    async def connect_proc(self, pid: int, websocket: WebSocket):
        instance = self.get_instance_by_pid(pid)
        if instance:
            await instance.connect_proc(websocket)
        else:
            raise BrokenPipeError(f"PID {pid} was not found on processor {self.proc.id}")

    async def disconnect_proc(self):
        raise NotImplementedError()

    def on_complete(self, with_errors):
        self.status = up_types.ProcessorExecutionStatus.COMPLETED

    def scale_down(self):
        pass

    def pause(self):
        pass

    def get_instance_by_pid(self, pid: int) -> Union[ProcessorInstance, None]:
        for i in self.instances:
            if i.pid == pid:
                return i
            if i.is_child_process(pid):
                return i
        return None

    def stats(self):
        try:
            instances_stats = []
            for i in self.instances:
                if i.stats is None:
                    continue
                instances_stats.append(i.stats)
            stats = ProcessorPerformanceStats(processor_id=self.id, instances_stats=instances_stats)
            return stats
        except Exception as e:
            print("Error on instance stats collection")
            print(str(e))


    def notify_termination(self, pid: int):
        instance = self.get_instance_by_pid(pid)
        if instance:
            instance.notify_termination()
        if self.pending_termination and len(self.running_instances) == 0:
            self.status = up_types.ProcessorExecutionStatus.COMPLETED
            return True
        return False

    def request_termination(self):
        for i in self.instances:
            i.request_termination()
        self.status = up_types.ProcessorExecutionStatus.PENDING_TERMINATION

    def launch_instance(self):
        if not self.proc.entry:
            raise EnvironmentError("Can not launch processor with no entry point")
        interpreter = self._interpreter_path
        if self.proc.interpreter:
            interpreter = self.proc.interpreter
        instance_type = InstanceType.SUB_PROCESS
        stdout_q = StdoutQueue()
        if self.proc.function:
            mod_name = pathlib.Path(self.proc.entry).stem
            mod_path = self.proc.entry
            mod_function = self.proc.function
            process = multiprocessing.Process(name=f"{mod_name}.{mod_function}", target=launch_module,
                                              args=(mod_name, mod_path, mod_function, stdout_q))
            process.daemon = True
            process.start()
            instance_type = InstanceType.PROCESS
        else:
            process = subprocess.Popen([interpreter, self.proc.entry], stdout=subprocess.PIPE)
        runner = ProcessorInstance(self.proc, process, instance_type, stdout_q)
        print(f"{self.proc.name} instance launched, pid: {runner.pid}")
        self._instances.append(runner)

    # def register_instance(self):
    #     if len(self.launched_instances) == 0:
    #         raise BrokenPipeError("Missing launch instances error")
    #     launched_instance = self.launched_instances[0]
    #     new_instance_id = self.allocate_new_instance_id()
    #     launched_instance.instance_id = new_instance_id
    #     launched_instance.state = InstanceState.RUNNING
    #     return new_instance_id
    #
    # def allocate_new_instance_id(self):
    #     last_instance_id = self._control_mem.read_int(self.LAST_INSTANCE_ID_POINTER)
    #     new_instance_id = last_instance_id + 1
    #     self._control_mem.write_int(self.LAST_INSTANCE_ID_POINTER, new_instance_id)
    #     return new_instance_id

    @property
    def executable(self):
        return self.proc.entry is not None

    @property
    def is_scaling(self):
        if len(self.launched_instances) > 0:
            return True
        return False

    @property
    def launched_instances(self):
        launched = [i for i in self._instances if i.state == InstanceState.LAUNCHED]
        if len(launched) > 1:
            raise BrokenPipeError("Duplicated launch instances error")
        return launched

    @property
    def instances(self):
        return self._instances

    @property
    def running_instances(self):
        return [i for i in self.instances if i.running]

    @property
    def running_instances_num(self):
        return len(self.running_instances)

    @property
    def name(self):
        return self.proc.name

    @property
    def id(self):
        return self.proc.id

    @property
    def cpu(self):
        return sum([i.cpu for i in self._instances])

    @property
    def memory(self):
        return sum([i.memory for i in self._instances])

    @property
    def pending(self):
        return sum([q.pending_counter for q in self.in_queues])

    @property
    def pending_termination(self):
        return self.status == up_types.ProcessorExecutionStatus.PENDING_TERMINATION

    @property
    def in_queues(self):
        return [q for q in self._queues if q.to_p == self.name]

    @property
    def out_queues(self):
        return [q for q in self._queues if q.from_p == self.name]

    @property
    def available_instances(self):
        if self.status == up_types.ProcessorExecutionStatus.COMPLETED:
            return 0
        if not self.executable:
            return 0
        allowed = self.proc.settings.autoscale - len(self._instances)
        if allowed < 0:
            raise EnvironmentError(f"Processor over scaled:f{self.proc.name}")
        return allowed

    @property
    def instances_number(self):
        return len(self._instances)

    def is_my_process(self, pid: int):
        for i in self.instances:
            if i.pid == pid:
                return True
            if i.is_child_process(pid):
                return True
        return False
