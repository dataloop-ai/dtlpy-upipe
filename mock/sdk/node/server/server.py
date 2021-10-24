import json
import pickle

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, Form
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.requests import Request

from mock.sdk.node.server import ProcessManager
from mock.sdk.types import API_Queue, API_Response, API_Proc, API_Proc_Message, NODE_PROC_NAME

# noinspection PyTypeChecker
manager: ProcessManager = None  # set on startup
fast_api = FastAPI()
# noinspection PyTypeChecker
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
    manager = ProcessManager(controller_proc_name)


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
