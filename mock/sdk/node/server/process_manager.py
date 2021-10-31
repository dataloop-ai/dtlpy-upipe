from typing import Dict

from fastapi import WebSocket

from mock.sdk import API_Pipe_Entity, API_Pipe_Message, API_Pipe, API_Queue


# noinspection PyTypeChecker
class ProcessManager:
    USAGE_HISTORY_LIMIT = 100
    SERVER_PID_POINTER = 0  # size 4, defined also in node_main.py

    def __init__(self):

        self.proc_connections: Dict[str, WebSocket] = {}
        self.ready = False
        self.pipes: Dict[str, API_Pipe] = {}
        self.node_proc: API_Pipe_Entity = None
        self.node_connection: WebSocket = None

    async def register_pipe(self, pipe: API_Pipe):
        self.pipes[pipe.name] = pipe

    async def connect(self, proc_name: str, websocket: WebSocket):
        await websocket.accept()
        if proc_name == self.node_proc.name:
            self.node_connection = websocket
            self.ready = True
        else:
            self.proc_connections[proc_name] = websocket

    def disconnect(self, proc_name: str, websocket: WebSocket):
        if proc_name == self.node_proc.name:
            self.node_connection = None
            self.ready = False
        else:
            del self.proc_connections[proc_name]

    async def send_message_to_node(self, msg: API_Pipe_Message):
        return await self.node_connection.send_json(msg)

    async def send_message_to_proc(self, msg: API_Pipe_Message):
        if msg.dest not in self.proc_connections:
            raise ConnectionError(f"No connection to {msg.dest}")
        return await self.proc_connections[msg.dest].send_json(msg)

    async def broadcast(self, message: str):
        for proc_name in self.proc_connections:
            connection = self.proc_connections[proc_name]
            await connection.send_json(message)
