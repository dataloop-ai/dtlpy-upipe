import asyncio
import json
import pickle
from typing import List, Dict
import os
import psutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, Form
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn
from starlette import status
from starlette.requests import Request

from mock.sdk.types import API_Queue, API_Response, API_Proc, ProcUtilizationEntry, API_Proc_Message, ProcMessageType, \
    NODE_PROC_NAME
from mock.sdk.entities.mem_queue import Queue
from mock.sdk.utils import SharedMemoryBuffer, MEMORY_ALLOCATION_MODE

node_shared_mem_name = "node_status"
node_shared_mem_size = 100
SERVER_PID_POINTER = 0  # size 4

server_proc_def = API_Proc(name="server", controller=True)
node_manager_proc_def = API_Proc(name=NODE_PROC_NAME, controller=True)


class NodeServer:
    _instance = None

    def __init__(self):
        print("Server ready")

    @staticmethod
    def instance():
        if NodeServer._instance is None:
            NodeServer._instance = NodeServer()
        return NodeServer._instance


class ProcessManager:
    USAGE_HISTORY_LIMIT = 100
    SERVER_PID_POINTER = 0  # size 4, defined also in node.py

    def __init__(self):
        self.proc_connections: Dict[str, WebSocket] = {}
        self.procs: Dict[str, API_Proc] = {}
        self.queues_defs: Dict[str, List[API_Queue]] = {}
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
        global controller_proc_name
        if controller_proc_name in self.proc_connections:
            msg = API_Proc_Message(type=ProcMessageType.PROC_REGISTER, dest=node_manager_proc_def,
                                   sender=server_proc_def)
            await self.proc_connections[controller_proc_name].send_json(msg.dict())

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
        for connection in self.proc_connections:
            await connection.send_json(message)


manager: ProcessManager = None  # set on startup
fast_api = FastAPI()
controller_proc_name: str = None


@fast_api.get("/")
def read_root():
    return {"Hello": "World"}


@fast_api.get("/serve")
async def serve():
    await manager.serve()
    if not manager.ready:
        return API_Response(success=False, code="NOT_READY", message="Server not ready")
    return API_Response(success=True)


@fast_api.get("/ping")
async def ping():
    return API_Response(success=True)


@fast_api.post("/register_proc")
async def register(proc: API_Proc):
    global controller_proc_name
    if proc.controller:
        await manager.register(proc)
        return API_Response(success=True, data={"messages": []})
    if not manager.ready:
        return API_Response(success=False, code="NOT_READY", message="Server not ready")
    await manager.register(proc)
    response = API_Response(success=True)
    q_defs = manager.get_queue_def_message(proc.name)
    response.messages.append(q_defs)
    return response


@fast_api.post("/register_q")
async def register_q(q: API_Queue):
    await manager.add_q(q.from_p, q)
    await manager.add_q(q.to_p, q)
    return {"Success": True}


@fast_api.post("/push_q")
async def push_q(q: str = Form(...), frame_file: UploadFile = Form(...)):
    q = API_Queue(**json.loads(q))
    contents = await frame_file.read()
    frame = pickle.loads(contents)
    added = await manager.put_in_q(q, frame)
    return {"Success": added}


@fast_api.on_event("startup")
async def startup_event():
    global manager
    print("network ready")
    manager = ProcessManager()
    loop = asyncio.get_event_loop()


@fast_api.websocket("/ws/connect/{proc_name}")
async def websocket_endpoint(websocket: WebSocket, proc_name: str):
    await manager.connect(proc_name, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg: API_Proc_Message = API_Proc_Message.parse_obj(json.loads(data))
                if msg.dest == NODE_PROC_NAME:
                    await manager.node_connection.send_json(msg.json())
                elif msg.dest in manager.proc_connections:
                    await manager.send_message(msg)
            except:
                raise ValueError("Un supported processor message")
    except WebSocketDisconnect:
        manager.disconnect(proc_name, websocket)
        # await manager.broadcast(f"Client #{proc_name} left the chat")


@fast_api.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


if __name__ == "__main__":
    uvicorn.run("server:fast_api", host="localhost", port=852, reload=False, log_level="warning")
