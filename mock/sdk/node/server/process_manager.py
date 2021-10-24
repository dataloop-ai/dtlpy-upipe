from typing import Dict, List

from mock.sdk import API_Proc, API_Queue, API_Proc_Message, ProcMessageType, NODE_PROC_NAME
from fastapi import WebSocket

from mock.sdk.entities import Queue
from mock.sdk.utils import SharedMemoryBuffer, MEMORY_ALLOCATION_MODE
import os

node_shared_mem_name = "node_status"
node_shared_mem_size = 100
SERVER_PID_POINTER = 0  # size 4

server_proc_def = API_Proc(name="server", controller=True)
node_manager_proc_def = API_Proc(name=NODE_PROC_NAME, controller=True)


class ProcessManager:
    USAGE_HISTORY_LIMIT = 100
    SERVER_PID_POINTER = 0  # size 4, defined also in node.py

    def __init__(self, controller_proc_name):
        self.controller_proc_name = controller_proc_name
        self.proc_connections: Dict[str, WebSocket] = {}
        self.procs: Dict[str, API_Proc] = {}
        self.queues_defs: Dict[str, List[API_Queue]] = {}
        # noinspection PyTypeChecker
        self.queues: List[Queue] = [None] * 50  # max Queues
        self.ready = False
        self.node_control_mem = SharedMemoryBuffer(node_shared_mem_name, node_shared_mem_size,
                                                   MEMORY_ALLOCATION_MODE.USE_ONLY)
        self.node_control_mem.write_int(self.SERVER_PID_POINTER, os.getpid())

    async def serve(self):
        self.ready = True

    def get_queue_def_message(self, proc_name: str) -> API_Proc_Message:
        q_json = {"queues": []}
        if proc_name in self.queues_defs:
            for q in self.queues_defs[proc_name]:
                q_json['queues'].append(q.dict())
        msg = API_Proc_Message(type=ProcMessageType.Q_UPDATE, dest=proc_name, sender=server_proc_def, body=q_json)
        return msg

    @property
    def node_connection(self):
        if NODE_PROC_NAME not in self.proc_connections:
            raise ConnectionError("Missing node connection")
        return self.proc_connections[NODE_PROC_NAME]

    async def connect(self, proc_name: str, websocket: WebSocket):
        await websocket.accept()
        self.proc_connections[proc_name] = websocket

    def disconnect(self, proc_name: str, websocket: WebSocket):
        del self.proc_connections[proc_name]

    async def register(self, proc: API_Proc):
        if self.controller_proc_name in self.proc_connections:
            msg = API_Proc_Message(type=ProcMessageType.PROC_REGISTER, dest=node_manager_proc_def,
                                   sender=server_proc_def)
            await self.proc_connections[self.controller_proc_name].send_json(msg.dict())

    async def init_q_mem(self, q: API_Queue):
        self.queues[q.q_id] = Queue(**q.dict())
        return

    async def put_in_q(self, q: API_Queue, frame):
        if not self.queues[q.q_id]:
            raise IndexError(f"Missing Q memory in server {q.q_id}")
        return await self.queues[q.q_id].put(frame)

    async def add_q(self, proc_name, q: API_Queue):
        if not self.queues[q.q_id] and q.host:
            await self.init_q_mem(q)
        if proc_name not in self.queues_defs:
            self.queues_defs[proc_name] = []
        self.queues_defs[proc_name].append(q)
        q_defs_message = self.get_queue_def_message(proc_name)
        await self.send_message(q_defs_message)

    async def send_message(self, message: API_Proc_Message):
        if message.dest not in self.proc_connections:
            return
        await self.proc_connections[message.dest].send_json(message.json())

    async def broadcast(self, message: str):
        for proc_name in self.proc_connections:
            connection = self.proc_connections[proc_name]
            await connection.send_json(message)
