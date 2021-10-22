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


from mock.sdk.types import API_Queue, API_Response, API_Proc, HW_Usage
from mock.sdk.entities.mem_queue import Queue
from mock.sdk.utils import SharedMemoryBuffer, MEMORY_ALLOCATION_MODE

node_shared_mem_name = "node_status"
node_shared_mem_size = 100
SERVER_PID_POINTER = 0 #size 4

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
        self.queues_defs: Dict[str, List[API_Queue]] = {}
        self.queues: List[Queue] = [None] * 50  # max Queues
        self.ready = False
        self.usage_history: List[HW_Usage] = []
        self.node_control_mem = SharedMemoryBuffer(node_shared_mem_name, node_shared_mem_size,
                                                   MEMORY_ALLOCATION_MODE.USE_ONLY)
        self.node_control_mem.write_int(self.SERVER_PID_POINTER, os.getpid())

    async def serve(self):
        self.ready = True

    async def report_hw_metrics(self):
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        usage = HW_Usage(cpu=cpu, memory=memory)
        self.usage_history.append(usage)
        if len(self.usage_history) > self.USAGE_HISTORY_LIMIT:
            del self.usage_history[0]

    async def auto_scale_required(self):
        cpu = 0
        memory = 0
        for u in self.usage_history:
            cpu += u.cpu
            memory += u.memory
        cpu /= len(self.usage_history)
        memory /= len(self.usage_history)
        if cpu < 75:
            return True
        return False

    def get_most_busy_q(self):
        max_pending = None
        max_q = None
        for q in self.queues:
            if not q:
                continue
            if max_pending is None:
                max_pending = q.pending_counter
                continue
            if q.pending_counter > max_pending:
                max_pending = q.pending_counter
                max_q = q
        return max_q

    async def auto_scale(self):
        q_to_scale = self.get_most_busy_q()
        if not q_to_scale:
            return
        proc_to_scale = q_to_scale.to_p
        if proc_to_scale not in self.proc_connections:
            return
        proc_connection = self.proc_connections[proc_to_scale]
        proc_connection.send_json()

    async def monitor(self):
        while True:
            # if self.execution_status == ProcessorExecutionStatus.RUNNING:
            #     await self.process_in_q()
            #     await asyncio.sleep(.1)
            # else:
            #     await asyncio.sleep(.5)
            await asyncio.sleep(1)
            await self.report_hw_metrics()
            if await self.auto_scale_required():
                await self.auto_scale()

    def get_queue_def(self, proc_name: str):
        q_json = {"type": "q_update", "queues": []}
        if not proc_name in self.queues_defs:
            return q_json
        for q in self.queues_defs[proc_name]:
            q_json['queues'].append(q.dict())
        return q_json

    async def connect(self, proc_name: str, websocket: WebSocket):
        await websocket.accept()
        self.proc_connections[proc_name] = websocket

    def disconnect(self, proc_name: str, websocket: WebSocket):
        del self.proc_connections[proc_name]

    async def register(self, proc_name: str):
        global controller_proc_name
        if controller_proc_name in self.proc_connections:
            await self.proc_connections[controller_proc_name].send_json({"type": "register", "proc_name": proc_name})
        q_defs = self.get_queue_def(proc_name)
        await self.send_message(proc_name, q_defs)

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
        q_defs = self.get_queue_def(proc_name)
        await self.send_message(proc_name, q_defs)

    async def send_message(self, proc_name: str, message: Dict):
        if proc_name not in self.proc_connections:
            return
        await self.proc_connections[proc_name].send_json(message)

    async def broadcast(self, message: str):
        for connection in self.proc_connections:
            await connection.send_json(message)


manager = None #set on startup
fast_api = FastAPI()
controller_proc_name: str = None



@fast_api.get("/")
def read_root():
    return {"Hello": "World"}


@fast_api.get("/serve")
async def serve():
    await manager.serve()
    if not manager.ready:
        return JSONResponse(content={"Success": False, "error": {"code": "NOT_READY", "message": "Server not ready"}})
    return JSONResponse(content={"Success": True})


@fast_api.get("/ping")
async def ping():
    return API_Response(success=True)


@fast_api.post("/register_proc")
async def register(proc: API_Proc):
    global controller_proc_name
    if proc.controller:
        controller_proc_name = proc.name
        await manager.register(proc.name)
        return API_Response(success=True)
    if not manager.ready:
        return API_Response(success=False, code="NOT_READY", message="Server not ready")
    await manager.register(proc.name)
    response = API_Response(success=True)
    q_defs = manager.get_queue_def(proc.name)
    if q_defs:
        response.data = {"messages": [q_defs]}
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
    loop.create_task(manager.monitor())


@fast_api.websocket("/ws/connect/{proc_name}")
async def websocket_endpoint(websocket: WebSocket, proc_name: str):
    await manager.connect(proc_name, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg['type'] == 'intra_proc':
                    await manager.send_message(msg['dest'], msg)
                if msg['type'] == 'broadcast':
                    await manager.broadcast(msg)
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
