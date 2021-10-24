import asyncio
import inspect
import multiprocessing
import pathlib
import socket
import time
import types
from queue import Empty
from threading import Thread

import numpy as np
from colorama import init, Fore, Back, Style
from enum import IntEnum
from io import StringIO
from multiprocessing.queues import Queue
from typing import Dict, List
import importlib
from mock.sdk import API_Node, API_Proc, ProcUtilizationEntry, QStatus, API_Proc_Message, ProcMessageType, \
    NodeUtilizationEntry, NODE_PROC_NAME
from .server import node_shared_mem_name, node_shared_mem_size, SERVER_PID_POINTER
import sys
import subprocess
import os
from .client import NodeClient

from configparser import ConfigParser
import uuid
import psutil

from ..entities.processor import Processor
from ..types.descriptors.network import API_Proc_Instance
from ..utils import processor_shared_memory_name, SharedMemoryBuffer, MEMORY_ALLOCATION_MODE

config_path = 'config.ini'
init(autoreset=True)


# This is a Queue that behaves like stdout
class StdoutQueue(Queue):
    def __init__(self, *args, **kwargs):
        ctx = multiprocessing.get_context()
        super(StdoutQueue, self).__init__(*args, **kwargs, ctx=ctx)

    def write(self, msg):
        self.put(msg)

    def flush(self):
        sys.__stdout__.flush()

    def readline(self):
        return None


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
        loop.run_until_complete(asyncio.sleep(3))  # some time for things to cleanup like connections
        loop.close()
    else:
        f()
    return True


class NodeConfig:
    def __init__(self):
        self.config = ConfigParser()
        if not os.path.exists(config_path):
            self.config['MACHINE_INFO'] = {'id': str(uuid.uuid4())}
            self._commit()
        else:
            self.config.read(config_path)

    def _commit(self):
        with open(config_path, 'w') as f:
            self.config.write(f)

    @property
    def node_id(self):
        return self.config.get('MACHINE_INFO', 'id')


def is_port_in_use(port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


class NodeStatus(IntEnum):
    UP = 1
    READY = 2
    RUNNING = 3


class ProcessType(IntEnum):
    MAIN = 1  # the process started the whole thing, usually pipeline script
    NODE_LOCAL_SERVER = 2  # the node server
    PROCESSOR = 3  # a launched processor


class InstanceType(IntEnum):
    PROCESS = 1
    SUB_PROCESS = 2


class ProcessorInstance:
    colors = [(Fore.WHITE, Back.BLACK), (Fore.RED, Back.GREEN), (Fore.BLUE, Back.WHITE), (Fore.BLACK, Back.WHITE),
              (Fore.RED, Back.WHITE),
              ]
    next_color_index = 0

    def __init__(self, proc, process, instance_id: int, instance_type=InstanceType.SUB_PROCESS, stdout_q=None):
        self.proc = proc
        self.process = process
        self.instance_id = instance_id
        self.instance_type = instance_type
        self.stdout_q = stdout_q
        self.color_index = ProcessorInstance.next_color_index
        ProcessorInstance.next_color_index += 1
        if ProcessorInstance.next_color_index >= len(self.colors):
            ProcessorInstance.next_color_index = 0
        thread = Thread(target=self.monitor)
        thread.start()

    def monitor(self):
        while True:
            if not self.is_alive:
                break
            if self.instance_type == InstanceType.SUB_PROCESS:
                self.stdout_q.write(self.process.stdout.readline())
            time.sleep(1)

    @property
    def color(self):
        return self.colors[self.color_index]

    @property
    def name(self):
        return self.proc.name

    @property
    def cpu(self):
        p = psutil.Process(self.process.pid)
        return p.cpu_percent()

    @property
    def memory(self):
        process = psutil.Process(self.process.pid)
        mem = process.memory_percent()
        return mem

    @property
    def exit_code(self):
        if self.instance_type == InstanceType.SUB_PROCESS:
            return self.process.poll()
        if self.instance_type == InstanceType.PROCESS:
            return self.process.exitcode
        return None

    def read_stdout_line(self):
        try:
            line = self.stdout_q.get(block=False)
        except Empty:
            line = None
        if self.instance_type == InstanceType.SUB_PROCESS and line:
            line = line.decode().strip()
        if not line or line == '\n' or len(line) == 0:
            return None
        line = f"{self.name}({self.instance_id})" + self.color[0] + self.color[1] + ">>>" + Style.RESET_ALL + f"{line}"
        return line

    @property
    def is_alive(self):
        return self.exit_code is None

    @property
    def api_def(self):
        return API_Proc_Instance(**self.proc, instance_id=self.instance_id, pid=self.process.pid)


class ProcessorController:
    ALIVE_POINTER = 0  # size 1
    LAST_INSTANCE_ID_POINTER = 1  # size 4

    def __init__(self, proc: API_Proc):
        self.proc = proc
        self._instances = []
        self._q_usage_log: Dict[str, list[QStatus]] = {}
        self._q_usage_log_size = 50
        self._interpreter_path = sys.executable
        processor_memory_name = processor_shared_memory_name(proc)
        size = Processor.SHARED_MEM_SIZE
        self._control_mem = SharedMemoryBuffer(processor_memory_name, size, MEMORY_ALLOCATION_MODE.USE_ONLY)

    def launch_instance(self):
        if not self.proc.entry:
            raise EnvironmentError("Can not launch processor with no entry point")
        new_instance_id = self._allocate_new_instance_id()
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
        runner = ProcessorInstance(self.proc, process, new_instance_id, instance_type, stdout_q)
        self._instances.append(runner)

    def log_q_usage(self, status: QStatus):
        if status.q_id not in self._q_usage_log:
            self._q_usage_log[status.q_id] = []
        log = self._q_usage_log[status.q_id]
        log.append(status)
        while len(log) > self._q_usage_log_size:
            del log[0]

    def _allocate_new_instance_id(self):
        last_instance_id = self._control_mem.read_int(self.LAST_INSTANCE_ID_POINTER)
        new_instance_id = last_instance_id + 1
        self._control_mem.write_int(self.LAST_INSTANCE_ID_POINTER, new_instance_id)
        return new_instance_id

    @property
    def executable(self):
        return self.proc.entry is not None

    @property
    def instances(self):
        return self._instances

    @property
    def name(self):
        return self.proc.name

    @property
    def cpu(self):
        return sum([i.cpu for i in self._instances])

    @property
    def memory(self):
        return sum([i.memory for i in self._instances])

    @property
    def pending(self):
        pending = 0
        for q_id in self._q_usage_log:
            log = self._q_usage_log[q_id]
            pending += int(np.mean([d.pending for d in log]))
        return pending

    @property
    def available_instances(self):
        if not self.executable:
            return 0
        allowed = self.proc.autoscale - len(self._instances)
        if allowed < 0:
            raise EnvironmentError(f"Processor over scaled:f{self.proc.name}")
        return allowed

    @property
    def instances_number(self):
        return len(self._instances)


# noinspection PyMethodMayBeStatic
class ComputeNode:
    NODE_USAGE_HISTORY_LIMIT = 30
    NODE_PID_POINTER = 4  # size 4, starts from 4 after server id
    config = NodeConfig()
    _instance = None

    async def waiter(self, event):
        print('waiting for it ...')
        await event.wait()
        self.on_frame_callback(self.get_current_message_data())

    @staticmethod
    def instance():
        if not ComputeNode._instance:
            ComputeNode._instance = ComputeNode()
        return ComputeNode._instance

    def __init__(self, name=None, host_name=None, port=None):  # name is unique per pipe
        self.name = name
        if not port:
            port = 852
        self.node_usage_history: List[NodeUtilizationEntry] = []
        self.port = port
        self.host_name = host_name
        self.node_id = self.config.node_id
        self.my_path = os.path.dirname(os.path.abspath(__file__))
        self.server_path = os.path.join(self.my_path, "server", "server.py")
        self.interpreter_path = sys.executable
        self.node_controller = False
        self.mem = None
        self.server_process = None
        self.node_client = NodeClient(NODE_PROC_NAME, self.on_ws_message)
        self.processors: Dict[str, ProcessorController] = {}
        self.utilization_log: Dict[str, list[ProcUtilizationEntry]] = {}
        self.utilization_log_size = 50
        self.last_scale_time = time.time()
        self.scale_block_time = 10  # time to wait before scaling again, seconds
        self.node_proc_def = API_Proc(name="node_manager", controller=True)

    def log_q_usage(self, sender: API_Proc, status: QStatus):
        self.processors[sender.name].log_q_usage(status)

    def on_ws_message(self, msg):
        proc_msg: API_Proc_Message = API_Proc_Message.parse_obj(msg)
        if proc_msg.type == ProcMessageType.Q_STATUS:
            self.log_q_usage(proc_msg.sender, QStatus.parse_obj(proc_msg.body))

    async def kill_process(self, pid):
        if pid == 0:
            return
        try:
            p = psutil.Process(pid)
            p.terminate()  # or p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

    async def kill_server(self):
        print("Closing old server")
        server_pid = None
        for process in psutil.process_iter():
            try:
                cmdline = process.cmdline()
                if self.server_path in cmdline:
                    server_pid = process.pid
                    break
            except psutil.AccessDenied:
                continue
        # server_pid = self.mem.read_int(SERVER_PID_POINTER)
        return await self.kill_process(server_pid)

    async def kill_node(self):
        print("Closing old node")
        await self.kill_server()
        node_pid = self.mem.read_int(self.NODE_PID_POINTER)
        return await self.kill_process(node_pid)

    # noinspection PyBroadException
    async def init_node(self):
        print("starting node server")
        if is_port_in_use(852):
            await self.kill_server()
        if is_port_in_use(852):
            sys.exit("Server port already in use")
        self.server_process = subprocess.Popen([self.interpreter_path, self.server_path])
        self.mem.write_int(SERVER_PID_POINTER, self.server_process.pid)
        self.mem.write_int(self.NODE_PID_POINTER, os.getpid())
        print("Waiting for localhost")
        while True:
            retry_time = 5
            try:
                await self.node_client.ping()
                break
            except:
                print(f"Server not available, retry in {retry_time} seconds")
                await asyncio.sleep(retry_time)
        if not await self.serve():
            print("No serving node, exit")
            sys.exit(-1)
        await self.node_client.connect()

    # noinspection PyBroadException
    async def init(self, name=None):
        if name:
            self.name = name
        if not self.name:
            self.name = f"node:{self.node_id}"
            print(f"Warning:Nameless node started:{self.name} by {sys.argv[0]}")
        else:
            print(f"Starting node:{self.name} by {sys.argv[0]}")
        try:
            self.mem = SharedMemoryBuffer(node_shared_mem_name, node_shared_mem_size,
                                          MEMORY_ALLOCATION_MODE.CREATE_ONLY)
        except MemoryError:
            self.mem = SharedMemoryBuffer(node_shared_mem_name, node_shared_mem_size,
                                          MEMORY_ALLOCATION_MODE.USE_ONLY)
            await self.kill_node()
        await self.init_node()

    def log_processor_utilization(self):
        for proc_name in self.processors:
            p = self.processors[proc_name]
            current_time = time.time() * 1000  # ms
            utilization = ProcUtilizationEntry(cpu=p.cpu, memory=p.memory, pending=p.pending, time=current_time,
                                               proc=p.proc)
            if proc_name not in self.utilization_log:
                self.utilization_log[proc_name] = []
            log = self.utilization_log[proc_name]
            log.append(utilization)
            while len(log) > self.utilization_log_size:
                del log[0]

    def log_hw_metrics(self):
        self.log_processor_utilization()
        self.log_node_utilization()
        # cpu = psutil.cpu_percent()
        # memory = psutil.virtual_memory().percent
        # usage = ProcUtilizationEntry(cpu=cpu, memory=memory)
        # self.usage_history.append(usage)
        # if len(self.usage_history) > self.USAGE_HISTORY_LIMIT:
        #     del self.usage_history[0]

    def log_node_utilization(self):
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        node_usage = NodeUtilizationEntry(cpu=cpu, memory=memory)
        self.node_usage_history.append(node_usage)
        while len(self.node_usage_history) > self.NODE_USAGE_HISTORY_LIMIT:
            del self.node_usage_history[0]

    def is_scale_down_required(self):
        if len(self.node_usage_history) == 0:
            return False
        time_since_last_autoscale = time.time() - self.last_scale_time
        if time_since_last_autoscale < self.scale_block_time:
            return False
        weights = [10 * (i+1) for i in range(len(self.node_usage_history))]
        cpu = int(np.ma.average([u.cpu for u in self.node_usage_history], weights=weights))
        memory = int(np.ma.average([u.memory for u in self.node_usage_history], weights=weights))
        print(Fore.GREEN + f"CPU:{cpu}%, MEM:{memory}%")
        if cpu > 85:
            return True
        if memory > 85:
            return True

    def is_scale_up_possible(self):
        time_since_last_autoscale = time.time() - self.last_scale_time
        if time_since_last_autoscale < self.scale_block_time:
            return False
        weights = [10 * (i+1) for i in range(len(self.node_usage_history))]
        cpu = int(np.ma.average([u.cpu for u in self.node_usage_history], weights=weights))
        memory = int(np.ma.average([u.memory for u in self.node_usage_history], weights=weights))
        # cpu = int(np.mean([u.cpu for u in self.node_usage_history]))
        # memory = int(np.mean([u.cpu for u in self.node_usage_history]))
        print(Fore.GREEN + f"CPU:{cpu}%, MEM:{memory}%")
        if cpu > 85:
            return False
        if memory > 85:
            return False
        scale_limit_reached = True
        for proc_name in self.processors:
            p = self.processors[proc_name]
            if p.available_instances > 0:
                scale_limit_reached = False
                break
        return not scale_limit_reached

    def get_processor_to_scale_up(self) -> ProcessorController:
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

    def get_processor_to_scale_down(self) -> ProcessorController:
        max_gap = None
        processor_to_scale_down = None
        for proc_name in self.processors:
            p = self.processors[proc_name]
            gap = p.proc.autoscale - p.instances_number
            if max_gap is None or gap > max_gap:
                max_gap = gap
                processor_to_scale_down = proc_name
        return self.processors[processor_to_scale_down]

    def scale_up(self):
        processor_to_scale: ProcessorController = self.get_processor_to_scale_up()
        print(f"scaling up:{processor_to_scale.name}")
        processor_to_scale.launch_instance()
        self.last_scale_time = time.time()

    def scale_down(self):
        processor_to_scale: ProcessorController = self.get_processor_to_scale_down()
        print(f"scaling down:{processor_to_scale.name}")
        termination_message = API_Proc_Message(sender=self.node_proc_def, type=ProcMessageType.PROC_TERMINATE,
                                               dest=processor_to_scale.proc.name)
        self.node_client.send_message(termination_message)
        self.last_scale_time = time.time()

    async def register_proc(self, proc: API_Proc):
        (data, messages) = await self.node_client.register_proc(proc)
        self.processors[proc.name] = ProcessorController(proc)
        return messages

    async def register(self):
        registered = await self.node_client.register_node(self.api_def)
        return registered

    async def serve(self):
        if await self.node_client.serve():
            print("serving")
            return True
        else:
            print("Error serving")
            return False

    async def start(self):
        pipe_complete = asyncio.Future()
        launched = 0
        for proc_name in self.processors:
            p: ProcessorController = self.processors[proc_name]
            if not p.executable:
                continue
            launched += 1
            p.launch_instance()
        print(f"Started {launched} processors")
        loop = asyncio.get_event_loop()
        loop.create_task(self.baby_sitter(pipe_complete))
        return pipe_complete

    def remove_instance(self, instance: ProcessorInstance):
        p = self.processors[instance.name]
        p.instances.remove(instance)

    def handle_instance_exit(self, code, instance: ProcessorInstance):
        if code == 0:
            print(f"{instance.name}({instance.instance_id}) >> ************Completed**************")
            self.remove_instance(instance)
            return

    async def baby_sitter(self, pipe_complete: asyncio.Future):
        startup_time = 1
        print("Process monitor on")
        await asyncio.sleep(startup_time)
        while True:
            await asyncio.sleep(1)
            running_instances = 0
            for proc_name in self.processors:
                p = self.processors[proc_name]
                for i in p.instances:
                    if i.is_alive:
                        running_instances += 1
                    exit_code = i.exit_code
                    if exit_code is not None:
                        self.handle_instance_exit(exit_code, i)
                        continue
                    for k in range(3):
                        line = i.read_stdout_line()
                        if line:
                            print(line)
                        else:
                            break
            if running_instances == 0:
                print("Pipe completed")
                pipe_complete.set_result(0)
                return
            self.log_hw_metrics()
            if self.is_scale_up_possible():
                self.scale_up()
            elif self.is_scale_down_required():
                self.scale_down()
        print("Cleanup ...")

    @property
    def api_def(self):
        return API_Node(name=self.name, host_name=self.host_name)
