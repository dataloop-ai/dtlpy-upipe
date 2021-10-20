import json
import pickle
from typing import List, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, Form, File
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
import uvicorn
from starlette import status
from starlette.requests import Request

from mock.sdk.types import API_Queue
from mock.sdk.mem_queue import Queue


class NodeServer:
    _instance = None

    def __init__(self):
        print("Server ready")

    @staticmethod
    def instance():
        if NodeServer._instance is None:
            NodeServer._instance = NodeServer()
        return NodeServer._instance


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.queues_defs: Dict[str, List[API_Queue]] = {}
        self.queues: List[Queue] = [None] * 50  # max Queues
        self.ready = False

    async def serve(self):
        self.ready = True

    def get_queue_def(self, proc_name: str):
        q_json = {"type": "q_update", "queues": []}
        if not proc_name in self.queues_defs:
            return q_json
        for q in self.queues_defs[proc_name]:
            q_json['queues'].append(q.dict())
        return q_json

    async def connect(self, proc_name: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[proc_name] = websocket

    def disconnect(self, proc_name: str, websocket: WebSocket):
        del self.active_connections[proc_name]

    async def register(self, proc_name: str):
        global controller_proc_name
        if controller_proc_name in self.active_connections:
            await self.active_connections[controller_proc_name].send_json({"type": "register", "proc_name": proc_name})
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
        if proc_name not in self.active_connections:
            return
        await self.active_connections[proc_name].send_json(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()
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


@fast_api.get("/register/{proc_name}")
async def register(proc_name: str):
    if not manager.ready:
        return JSONResponse(content={"Success": False, "error": {"code": "NOT_READY", "message": "Server not ready"}})
    await manager.register(proc_name)
    q_defs = manager.get_queue_def(proc_name)
    return JSONResponse(content={"Success": True, "messages": [q_defs]})


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


@fast_api.get("/register_controller/{proc_name}")
def register_controller(proc_name: str):
    global controller_proc_name
    controller_proc_name = proc_name
    return {"Success": True, "messages": []}


@fast_api.on_event("startup")
async def startup_event():
    print("network ready")


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
