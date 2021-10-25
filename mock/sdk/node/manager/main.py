import asyncio
import os
import socket
import subprocess
import sys
import time
import uuid
from configparser import ConfigParser
from enum import IntEnum
from typing import Dict, List

import numpy as np
import psutil
from colorama import init, Fore, Back

from mock.sdk import API_Node, API_Proc, ProcUtilizationEntry, QStatus, API_Proc_Message, ProcMessageType, \
    NodeUtilizationEntry, NODE_PROC_NAME
from mock.sdk.node.client import NodeClient
from mock.sdk.node.server import node_shared_mem_name, node_shared_mem_size, SERVER_PID_POINTER

from .process_controller import ProcessorController
from .processor_instance import ProcessorInstance
from ...utils import SharedMemoryBuffer, MEMORY_ALLOCATION_MODE

config_path = 'config.ini'
init(autoreset=True)


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


# noinspection PyMethodMayBeStatic
class ComputeNode:
    NODE_USAGE_HISTORY_LIMIT = 30
    NODE_PID_POINTER = 4  # size 4, starts from 4 after server id
    config = NodeConfig()
    _instance = None

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
        self.server_path = os.path.join(self.my_path, "../server", "server.py")
        self.interpreter_path = sys.executable
        self.node_controller = False
        self.mem = None
        self.server_process = None
        self.node_client = NodeClient(NODE_PROC_NAME, self.on_ws_message)
        self.processors: Dict[str, ProcessorController] = {}
        self.utilization_log: Dict[str, List[ProcUtilizationEntry]] = {}
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
        weights = [10 * (i + 1) for i in range(len(self.node_usage_history))]
        cpu = int(np.ma.average([u.cpu for u in self.node_usage_history], weights=weights))
        memory = int(np.ma.average([u.memory for u in self.node_usage_history], weights=weights))
        # print(Fore.GREEN + f"CPU:{cpu}%, MEM:{memory}%")
        if cpu > 90:
            return True
        if memory > 90:
            return True

    def is_scale_up_possible(self):
        time_since_last_autoscale = time.time() - self.last_scale_time
        if time_since_last_autoscale < self.scale_block_time:
            return False
        weights = [10 * (i + 1) for i in range(len(self.node_usage_history))]
        cpu = int(np.ma.average([u.cpu for u in self.node_usage_history], weights=weights))
        memory = int(np.ma.average([u.memory for u in self.node_usage_history], weights=weights))
        # cpu = int(np.mean([u.cpu for u in self.node_usage_history]))
        # memory = int(np.mean([u.cpu for u in self.node_usage_history]))
        print(Fore.GREEN + f"CPU:{cpu}%, MEM:{memory}%")
        if cpu > 70:
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
        print(Fore.BLUE + f"scaling up:{processor_to_scale.name}")
        processor_to_scale.launch_instance()
        self.last_scale_time = time.time()

    def scale_down(self):
        processor_to_scale: ProcessorController = self.get_processor_to_scale_down()
        print(Fore.BLUE + f"scaling down:{processor_to_scale.name}")
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

    def on_pipe_cleanup(self):
        pass

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
                    if i.is_done:
                        line = i.read_stdout_line()
                        while line:
                            print(line)
                            line = i.read_stdout_line()
                        self.handle_instance_exit(i)
                        continue
                    running_instances += 1
                    for k in range(3):
                        line = i.read_stdout_line()
                        if line:
                            print(line)
                        else:
                            break
            if running_instances == 0:
                print(Fore.CYAN + Back.GREEN + "Pipe completed ...")
                self.on_pipe_cleanup()
                pipe_complete.set_result(0)
                return
            self.log_hw_metrics()
            if self.is_scale_up_possible():
                self.scale_up()
            elif self.is_scale_down_required():
                self.scale_down()

    @property
    def api_def(self):
        return API_Node(name=self.name, host_name=self.host_name)
