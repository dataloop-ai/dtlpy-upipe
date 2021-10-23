import asyncio
import socket
from enum import IntEnum
from multiprocessing import shared_memory
from typing import Dict, List

from mock.sdk import API_Node, API_Proc
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


class ProcessorInstance:
    def __init__(self, proc, process, instance_id: int):
        self.proc = proc
        self.process = process
        self.instance_id = instance_id

    @property
    def name(self):
        return self.proc.name

    @property
    def api_def(self):
        return API_Proc_Instance(**self.proc, instance_id=self.instance_id, pid=self.process.pid)


class ProcessorController:
    ALIVE_POINTER = 0  # size 1
    LAST_INSTANCE_ID_POINTER = 1  # size 4

    def __init__(self, proc: API_Proc):
        self.proc = proc
        self._instances = []
        self.interpreter_path = sys.executable
        processor_memory_name = processor_shared_memory_name(proc)
        size = Processor.SHARED_MEM_SIZE
        self.control_mem = SharedMemoryBuffer(processor_memory_name, size, MEMORY_ALLOCATION_MODE.USE_ONLY)

    def launch_instance(self):
        if not self.proc.entry:
            raise EnvironmentError("Can not launch processor with no entry point")
        new_instance_id = self._allocate_new_instance_id()
        interpreter = self.interpreter_path
        if self.proc.interpreter:
            interpreter = self.proc.interpreter
        process = subprocess.Popen([interpreter, self.proc.entry], stdout=subprocess.PIPE)
        runner = ProcessorInstance(self.proc, process, new_instance_id)
        self._instances.append(runner)

    def _allocate_new_instance_id(self):
        last_instance_id = self.control_mem.read_int(self.LAST_INSTANCE_ID_POINTER)
        new_instance_id = last_instance_id + 1
        self.control_mem.write_int(self.LAST_INSTANCE_ID_POINTER, new_instance_id)
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


class ComputeNode:
    NODE_PID_POINTER = 4 #size 4, starts from 4 after server id
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
        self.port = port
        self.host_name = host_name
        self.node_id = self.config.node_id
        self.my_path = os.path.dirname(os.path.abspath(__file__))
        self.server_path = os.path.join(self.my_path, "server", "server.py")
        self.interpreter_path = sys.executable
        self.node_controller = False
        self.mem = None
        self.server_process = None
        self.node_client = NodeClient("node-main")
        self.processors: Dict[str, ProcessorController] = {}

    async def kill_process(self, pid):
        if pid == 0:
            return
        p = psutil.Process(pid)
        p.terminate()  # or p.kill()

    async def kill_server(self):
        print("Closing old server")
        server_pid = self.mem.read_int(SERVER_PID_POINTER)
        return await self.kill_process(server_pid)

    async def kill_node(self):
        print("Closing old node")
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
            self.mem = SharedMemoryBuffer(node_shared_mem_name, node_shared_mem_size, MEMORY_ALLOCATION_MODE.CREATE_ONLY)
        except MemoryError:
            self.mem = SharedMemoryBuffer(node_shared_mem_name, node_shared_mem_size,
                                          MEMORY_ALLOCATION_MODE.USE_ONLY)
            await self.kill_node()
        await self.init_node()

    async def register_proc(self, proc: API_Proc):
        messages = await self.node_client.register_proc(proc)
        self.processors[proc.name] = ProcessorController(proc)
        return messages

    async def register(self):
        registered = await self.node_client.register_node(self.api_def, self.on_ws_message)
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
        print("Process monitor on")
        while True:
            await asyncio.sleep(.1)
            for proc_name in self.processors:
                running_instances = 0
                p = self.processors[proc_name]
                for i in p.instances:
                    exit_code = i.process.poll()
                    if exit_code is not None:
                        self.handle_instance_exit(exit_code, i)
                    running_instances += 1
                    line = i.process.stdout.readline()
                    if line:
                        print(f"{i.name}({i.instance_id})>>>{line.decode().strip()}")
            if running_instances == 0:
                print("Pipe completed")
                pipe_complete.set_result(0)
                return

    @property
    def api_def(self):
        return API_Node(name=self.name, host_name=self.host_name)
