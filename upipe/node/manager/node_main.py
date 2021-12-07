import asyncio
import socket
import subprocess
import psutil
import sys
import os
import time
from enum import IntEnum
from typing import Dict, List, Tuple, Union

import numpy as np
import requests
from colorama import init, Fore, Back
from fastapi import WebSocket

from ... import entities, types, utils
from .node_config import NodeConfig
from ..client import NodeClient
from .pipe_controller import PipeController
from .node_utils import kill_em_all, get_process_by_path, count_process_by_path
from ...types import UPipeEntityType
from ...types.pipe import PipelineAlreadyExist

init(autoreset=True)

node_shared_mem_name: str = "node_status"
node_shared_mem_size: int = 4096


def is_port_in_use(port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


class NodeStatus(IntEnum):
    UP = 1
    READY = 2
    RUNNING = 3


NODE_MANAGER_PROC_NAME = "upipe-node-manager"


# noinspection PyMethodMayBeStatic
class ComputeNode:
    SERVER_PID_POINTER = 0  # size 4
    NODE_PID_POINTER = 4  # size 4, starts from 4 after server id
    NODE_HOST_URL_POINTER = 100  # size 255,
    NODE_HOST_URL_SIZE = 255
    NODE_USAGE_HISTORY_LIMIT = 30
    config = NodeConfig()
    _instance = None
    node_root_path = os.path.dirname(os.path.abspath(__file__))
    node_path = os.path.join(node_root_path, "node_main.py")
    server_path = os.path.join(node_root_path, "..", "server", "server.py")
    interpreter_path = sys.executable
    host_name = 'localhost'
    port = 852

    @staticmethod
    def root_path():
        return os.path.dirname(os.path.abspath(__file__))

    # noinspection PyTypeChecker
    def __init__(self):  # name is unique per pipe
        self.name = NODE_MANAGER_PROC_NAME
        self.node_id = self.config.machine_id
        self.primary_instance = False
        self.mem: utils.SharedMemoryBuffer = None
        self.server_process = None
        self.node_usage_history: List[types.NodeUtilizationEntry] = []
        self.last_scale_time = time.time()
        self.scale_block_time = 10  # time to wait before scaling again, seconds
        self.pipe_controllers: Dict[str, PipeController] = {}
        self._node_ready = False

    def get_proc_queues(self, proc_id: str) -> types.APIProcQueues:
        queues = types.APIProcQueues(proc_id=proc_id)
        for p in self.pipe_controllers:
            pipe: PipeController = self.pipe_controllers[p]
            for qid in pipe.queues:
                queue = pipe.queues[qid]
                if queue.from_p == proc_id or queue.to_p == proc_id:
                    api_q: types.APIQueue = queue.queue_def
                    queues.queues[api_q.id] = api_q
        return queues

    def register_launched_instance(self, pid: int, proc: types.UPipeEntity) -> Tuple[int, dict]:
        from .. import ProcessorInstance  ## TODO, circular dependency to resovle
        launched_processor: Union[ProcessorInstance, None] = None
        for p in self.pipe_controllers:
            pipe: PipeController = self.pipe_controllers[p]
            instance = pipe.get_instance_by_pid(pid)
            if instance is None:
                continue
            if not instance.is_launched:
                raise BrokenPipeError("Instance already registered: {!r} ({})".format(instance.name, instance.pid))
            launched_processor = instance
            break
        if not launched_processor:
            available_processors = ', '.join(
                [key for pipe in self.pipe_controllers.values() for key in pipe.processors.keys()])
            print("Instance launch error: {!r}. available: {}".format(proc.id, available_processors))
            raise BrokenPipeError("Missing launched instance pid : {!r}".format(pid))
        launched_processor.register(pid)
        return launched_processor

    @staticmethod
    def launch_server(host='localhost', port=852):
        my_env = os.environ.copy()
        my_env["UPIPE_HOST"] = host
        my_env["UPIPE_PORT"] = str(port)
        kill_em_all(ComputeNode.server_path, False)
        # init server
        server_process = subprocess.Popen([ComputeNode.interpreter_path, ComputeNode.server_path], env=my_env)
        print(f"Launching new server {server_process.pid}")
        return server_process

    @staticmethod
    def kill_em_all():
        kill_em_all(ComputeNode.node_path, False)
        kill_em_all(ComputeNode.server_path, False)

    def allocate_memory(self):
        try:
            self.mem = utils.SharedMemoryBuffer(node_shared_mem_name,
                                                node_shared_mem_size,
                                                utils.MEMORY_ALLOCATION_MODE.CREATE_ONLY)
            self.primary_instance = True
        except MemoryError:
            raise MemoryError("Unable to allocate node memory")

    @staticmethod
    def server_base_url():
        return f"{ComputeNode.host_name}:{ComputeNode.port}"

    @staticmethod
    def is_node_memory_allocated():
        try:
            utils.SharedMemoryBuffer(node_shared_mem_name,
                                     node_shared_mem_size,
                                     utils.MEMORY_ALLOCATION_MODE.USE_ONLY)
        except MemoryError:
            return False
        return True

    @staticmethod
    def is_node_ready():
        if not ComputeNode.is_node_memory_allocated():
            return False
        if not ComputeNode.is_server_process_alive():
            return False
        if not ComputeNode.is_server_available():
            return False
        return True

    @staticmethod
    def is_server_process_alive():
        server_process = get_process_by_path(ComputeNode.server_path)
        if not server_process:
            return False
        return True

    @staticmethod
    def nodes_process_count():
        return count_process_by_path(ComputeNode.server_path)

    @staticmethod
    def is_server_available():
        server_base_url = ComputeNode.server_base_url()
        ping_url = f"http://{server_base_url}/ping"
        try:
            res = requests.get(ping_url)
            return res.status_code == 200
        except Exception:
            return False

    @staticmethod
    def is_node_process_alive():
        return ComputeNode.get_node_process() is not None

    @staticmethod
    def get_node_process():
        node_process = get_process_by_path(ComputeNode.node_path)
        return node_process

    def load_pipe(self, pipe: types.APIPipe):
        if pipe.id in self.pipe_controllers:
            raise PipelineAlreadyExist(pipe.id)
        p = PipeController(self.proc_def)
        p.load(pipe)
        self.pipe_controllers[pipe.id] = p

    async def attach_proc(self, pid: int, websocket: WebSocket):
        for pipe_name in self.pipe_controllers:
            pipe = self.pipe_controllers[pipe_name]
            await pipe.connect_proc(pid, websocket)

    async def attach_pipe(self, pipe_id: str, websocket: WebSocket):
        if pipe_id in self.pipe_controllers:
            pipe = self.pipe_controllers[pipe_id]
            await pipe.connect_pipe(websocket)

    def process_message(self, proc_msg: types.UPipeMessage):
        try:
            if proc_msg.scope == types.UPipeEntityType.PIPELINE:
                if proc_msg.dest not in self.pipe_controllers:
                    raise IndexError("Message : Pipe does not exist")
                self.pipe_controllers[proc_msg.dest].process_message(proc_msg)
            if proc_msg.scope == types.UPipeEntityType.PROCESSOR:
                for pipe_name in self.pipe_controllers:
                    pipe = self.pipe_controllers[pipe_name].process_message(proc_msg)
        except Exception as e:
            print(f"Error on node message : {str(e)}")

    def on_ws_message(self, proc_msg: types.UPipeMessage):
        self.process_message(proc_msg)

    def connect(self):
        self.node_client.connect()
        self._node_ready = True

    async def push_q(self, q: types.APIQueue, df: entities.DataFrame):
        for pipe_name in self.pipe_controllers:
            pipe = self.pipe_controllers[pipe_name]
            if q.id in pipe.queues:
                queue: entities.MemQueue = pipe.queues[q.id]
                return await queue.put(df)
        return False

    async def wait_for_node_ready(self, timeout=10):
        start_time = time.time()
        while not self._node_ready:
            await asyncio.sleep(.5)
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError("Timeout waiting for node initialization")

    def start(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.baby_sitter())

    def check_autoscale(self):
        # check no active scaling
        for pipe_name in self.pipe_controllers:
            p = self.pipe_controllers[pipe_name]
            if p.is_scaling:
                return
        # check scale down
        if self.is_scale_down_required():
            pipes_available_to_scale_down = []
            self.last_scale_time = time.time()
            for pipe_name in self.pipe_controllers:
                p = self.pipe_controllers[pipe_name]
                if p.is_scaled:
                    pipes_available_to_scale_down.append(pipe_name)
            if len(pipes_available_to_scale_down) == 0:
                return
            pipe_to_scale_down = pipes_available_to_scale_down[0]
            self.pipe_controllers[pipe_to_scale_down].scale_down()
            self.last_scale_time = time.time()
            return
        # check scale up
        if not self.is_scale_up_possible():
            return
        pipes_available_to_scale = []
        for pipe_name in self.pipe_controllers:
            p = self.pipe_controllers[pipe_name]
            if not p.scaled_to_maxed:
                pipes_available_to_scale.append(pipe_name)
        if len(pipes_available_to_scale) == 0:
            return
        pipe_to_scale = pipes_available_to_scale[0]
        self.pipe_controllers[pipe_to_scale].scale_up()
        self.last_scale_time = time.time()

    def log_node_utilization(self):
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        node_usage = types.NodeUtilizationEntry(cpu=cpu, memory=memory)
        self.node_usage_history.append(node_usage)
        while len(self.node_usage_history) > self.NODE_USAGE_HISTORY_LIMIT:
            del self.node_usage_history[0]
        for pipe_name in self.pipe_controllers:
            p = self.pipe_controllers[pipe_name]
            p.log_pipe_utilization()

    def is_scale_down_required(self):
        if len(self.node_usage_history) == 0:
            return False
        time_since_last_autoscale = time.time() - self.last_scale_time
        if time_since_last_autoscale < self.scale_block_time:
            return False
        weights = [i ** 2 for i in range(len(self.node_usage_history))]
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
        weights = [i ** 2 for i in range(len(self.node_usage_history))]
        cpu = int(np.ma.average([u.cpu for u in self.node_usage_history], weights=weights))
        memory = int(np.ma.average([u.memory for u in self.node_usage_history], weights=weights))
        # cpu = int(np.mean([u.cpu for u in self.node_usage_history]))
        # memory = int(np.mean([u.cpu for u in self.node_usage_history]))
        print(Fore.GREEN + f"CPU:{cpu}%, MEM:{memory}%")
        if cpu > 70:
            return False
        if memory > 85:
            return False
        return True

    #
    # def send_pipe_status(self, status: PipeExecutionStatus):
    #     status_message = API_Pipe_Status_Message(sender=self.proc_def, type=PipeMessageType.PIPE_STATUS,
    #                                              dest=server_proc_def, status=status, scope=PipeEntityType.SERVER,
    #                                              pipe_name=self.name)
    #     self.node_client.send_message(status_message)

    def monitor_pipe(self, pipe_name):
        pipe = self.pipe_controllers[pipe_name]
        running_instances = 0
        for proc_name in pipe.processors:
            p = pipe.processors[proc_name]
            for i in p.instances:
                if i.is_done:
                    line = i.read_stdout_line()
                    while line:
                        print(line)
                        line = i.read_stdout_line()
                    pipe.handle_instance_exit(i)
                    continue
                running_instances += 1
                for k in range(3):
                    line = i.read_stdout_line()
                    if line:
                        print(line)
                    else:
                        break
        return running_instances

    @property
    def running_pipes_count(self):
        count = 0
        for pipe_name in self.pipe_controllers:
            pipe: PipeController = self.pipe_controllers[pipe_name]
            if pipe.running:
                count += 1
        return count

    async def baby_sitter(self):
        startup_time = 1
        print("Process monitor on")
        waiting_print = "Waiting for pipe start"
        await asyncio.sleep(startup_time)
        if self.running_pipes_count == 0:
            print(waiting_print)
        while True:
            await asyncio.sleep(1)
            if self.running_pipes_count == 0:
                continue
            for pipe_name in self.pipe_controllers:
                pipe = self.pipe_controllers[pipe_name]
                running_instances = self.monitor_pipe(pipe_name)
                if running_instances == 0:
                    print(Fore.CYAN + Back.GREEN + f"Pipe {pipe_name} completed ...")
                    pipe.cleanup()
            self.log_node_utilization()
            self.check_autoscale()
            if self.running_pipes_count == 0:
                print(waiting_print)

    @property
    def api_def(self):
        return types.APINode(id=self.name, type=UPipeEntityType.NODE, controller=False, name=self.name,
                             host_name=self.host_name)

    @property
    def proc_def(self):
        return types.UPipeEntity(name=NODE_MANAGER_PROC_NAME,
                                 id=NODE_MANAGER_PROC_NAME,
                                 type=types.UPipeEntityType.NODE)