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

from upipe.node.manager import ComputeNode
from upipe import types

server_proc_def = types.APIPipeEntity(name="upipe-local-server",
                                      id="upipe-local-server",
                                      type=types.PipeEntityType.SERVER)

fast_api = FastAPI()

node = ComputeNode()


@fast_api.get("/")
def read_root():
    return {"Hello": "World"}


@fast_api.get("/ping")
async def ping():
    return types.APIResponse(success=True)


@fast_api.post("/register_proc")
async def register_proc(proc: types.APIPipeEntity):
    queues_def = node.get_proc_queues(proc.name)
    instance_id, config = node.register_proc_instance(proc.name)
    registration_info = {"instance_id": instance_id}
    q_update_msg = types.APIPipeMessage(dest=proc.name,
                                        sender=server_proc_def.id,
                                        type=types.PipeMessageType.Q_UPDATE,
                                        body=queues_def,
                                        scope=types.PipeEntityType.PROCESSOR)
    config_update_msg = types.APIPipeMessage(dest=proc.name,
                                             sender=server_proc_def.id,
                                             type=types.PipeMessageType.CONFIG_UPDATE,
                                             body=config,
                                             scope=types.PipeEntityType.PROCESSOR)
    registration_update_msg = types.APIPipeMessage(dest=proc.name,
                                                   sender=server_proc_def.id,
                                                   type=types.PipeMessageType.REGISTRATION_INFO,
                                                   body=registration_info,
                                                   scope=types.PipeEntityType.PROCESSOR)
    return types.APIResponse(success=True, messages=[registration_update_msg, q_update_msg, config_update_msg])


@fast_api.post("/register_pipe")
async def register_pipe(pipe: types.APIPipe):
    try:
        # msg: API_Pipe_Message = API_Pipe_Message(sender=server_proc_def, dest=manager.node_proc.name,
        #                                          type=PipeMessageType.PIPE_REGISTER,
        #                                          body=pipe, scope=PipeEntityType.NODE)
        global node
        node.register_pipe(pipe)
        # await manager.register_pipe(pipe)
        # await manager.node_connection.send_json(msg.dict())
        return types.APIResponse(success=True, data=server_proc_def.dict())
    except Exception:
        return types.APIResponse(success=False, text=f"Error registering pipe")


@fast_api.post("/push_q")
async def push_q(q: str = Form(...), frame_file: UploadFile = Form(...)):
    q = types.APIQueue(**json.loads(q))
    contents = await frame_file.read()
    frame = pickle.loads(contents)
    added = await node.push_q(q, frame)
    return types.APIResponse(success=added)


@fast_api.on_event("startup")
async def startup_event():
    global node
    print("network ready")
    node.start()
    print("Server ready")
    return


async def handle_server_message(message: types.APIPipeMessage):
    pass


msg_counter = 0


@fast_api.websocket("/ws/connect/{proc_name}")
async def websocket_endpoint(websocket: WebSocket, proc_name: str):
    global msg_counter
    await node.attach(proc_name, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_counter += 1
            try:
                proc_msg: types.APIPipeMessage = types.parse_pipe_message(json.loads(data))
                if proc_msg.scope == types.PipeEntityType.SERVER:
                    await handle_server_message(msg)
                else:
                    node.process_message(proc_msg)
            except Exception:
                raise ValueError("Un supported processor message")
    except WebSocketDisconnect:
        await node.detach(proc_name, websocket)
        # await manager.broadcast(f"Client #{proc_name} left the chat")


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
