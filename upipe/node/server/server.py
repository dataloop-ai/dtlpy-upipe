import json
import pickle
import os
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, Form
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.requests import Request
from upipe.node.server.node_controller import node
from upipe import types
from upipe.node.server import view_api
from fastapi.middleware.cors import CORSMiddleware

from upipe.types.pipe import PipelineAlreadyExist

server_proc_def = types.UPipeEntity(name="upipe-local-server",
                                    id="upipe-local-server",
                                    type=types.UPipeEntityType.SERVER)

origins = [
    "http://localhost",
    "http://localhost:8080",
]

fast_api = FastAPI()
fast_api.include_router(view_api.router)
fast_api.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@fast_api.get("/")
def read_root():
    return {"Hello": "World"}


@fast_api.get("/ping")
async def ping():
    return types.APIResponse(success=True)


@fast_api.post("/register_proc/{pid}")
async def register_proc(pid: str, proc: types.UPipeEntity):
    instance = node.register_launched_instance(int(pid), proc)
    config = instance.proc.config
    data = {"config": config}
    registration_info = {"instance_id": pid}
    queues_def = node.get_proc_queues(instance.proc.id)
    q_update_msg = types.UPipeMessage(dest=instance.proc.id,
                                      sender=server_proc_def.id,
                                      type=types.UPipeMessageType.Q_UPDATE,
                                      body=queues_def,
                                      scope=types.UPipeEntityType.PROCESSOR)
    registration_update_msg = types.UPipeMessage(dest=instance.proc.id,
                                                 sender=server_proc_def.id,
                                                 type=types.UPipeMessageType.REGISTRATION_INFO,
                                                 body=registration_info,
                                                 scope=types.UPipeEntityType.PROCESSOR)
    return types.APIResponse(success=True, data=data, messages=[registration_update_msg, q_update_msg])


# noinspection PyBroadException
@fast_api.post("/load_pipe")
async def load_pipe(pipe: types.APIPipe):
    try:
        node.load_pipe(pipe)
        return types.APIResponse(success=True, data=server_proc_def.dict())
    except PipelineAlreadyExist as e:
        return types.APIResponse(success=False, text=e.message)
    except Exception as e:
        return types.APIResponse(success=False, text=f"Error loading pipe:{str(e)}")


@fast_api.post("/push_q")
async def push_q(q: str = Form(...), frame_file: UploadFile = Form(...)):
    q = types.APIQueue(**json.loads(q))
    contents = await frame_file.read()
    frame = pickle.loads(contents)
    added = await node.push_q(q, frame)
    return types.APIResponse(success=added)


@fast_api.on_event("startup")
async def startup_event():
    print("network ready")
    node.start()
    print("Server ready")
    return


async def handle_server_message(message: types.UPipeMessage):
    pass


msg_counter = 0

@fast_api.websocket("/ws/proc/{pid}")
async def proc_websocket_endpoint(websocket: WebSocket, pid: str):
    await node.attach_proc(int(pid), websocket)
    try:
        await ws_monitor(websocket)
    except WebSocketDisconnect:
        return

@fast_api.websocket("/ws/pipe/{pipe_id}")
async def pipe_websocket_endpoint(websocket: WebSocket, pipe_id: str):
    await node.attach_pipe(pipe_id, websocket)
    try:
        await ws_monitor(websocket)
    except WebSocketDisconnect:
        return

async def ws_monitor(websocket: WebSocket):
    global msg_counter
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_counter += 1
            try:
                proc_msg: types.UPipeMessage = types.parse_pipe_message(json.loads(data))
                if proc_msg.scope == types.UPipeEntityType.SERVER:
                    await handle_server_message(msg)
                else:
                    node.process_message(proc_msg)
            except Exception as e:
                raise ValueError("Un supported processor message")
    except WebSocketDisconnect:
        raise WebSocketDisconnect
    except Exception as e:
        raise ValueError("Error parsing message")

@fast_api.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


if __name__ == "__main__":
    HOST = os.getenv('UPIPE_HOST')
    if HOST is None:
        HOST = "localhost"
    PORT = os.getenv('UPIPE_PORT')
    if PORT is None:
        PORT = 852
    PORT = int(PORT)
    print(f"Starting upipe server {os.getpid()} @ {HOST}:{PORT}")
    uvicorn.run("server:fast_api", host=HOST, port=PORT, reload=False, log_level="warning")
