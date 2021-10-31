import json
import pickle

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, Form
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.requests import Request
from mock.sdk.types import API_Queue, API_Response, API_Pipe_Entity, API_Pipe_Message, PipeMessageType, \
    API_Pipe, PipeEntityType, parse_pipe_message
from mock.sdk.node.manager.node_main import ComputeNode

server_proc_def = API_Pipe_Entity(name="upipe-local-server",id="upipe-local-server", type=PipeEntityType.SERVER)

fast_api = FastAPI()

node = ComputeNode()


@fast_api.get("/")
def read_root():
    return {"Hello": "World"}


@fast_api.get("/ping")
async def ping():
    return API_Response(success=True)


@fast_api.post("/register_proc")
async def register_proc(proc: API_Pipe_Entity):
    queues_def = node.get_proc_queues(proc.name)
    instance_id, config = node.register_proc_instance(proc.name)
    registration_info = {"instance_id": instance_id}
    q_update_msg = API_Pipe_Message(dest=proc.name, sender=server_proc_def.id,
                                    type=PipeMessageType.Q_UPDATE, body=queues_def, scope=PipeEntityType.PROCESSOR)
    config_update_msg = API_Pipe_Message(dest=proc.name, sender=server_proc_def.id,
                                         type=PipeMessageType.CONFIG_UPDATE, body=config, scope=PipeEntityType.PROCESSOR)
    registration_update_msg = API_Pipe_Message(dest=proc.name, sender=server_proc_def.id,
                                               type=PipeMessageType.REGISTRATION_INFO, body=registration_info,
                                               scope=PipeEntityType.PROCESSOR)
    return API_Response(success=True, messages=[registration_update_msg, q_update_msg, config_update_msg])


# noinspection PyBroadException
@fast_api.post("/register_pipe")
async def register_pipe(pipe: API_Pipe):
    try:
        # msg: API_Pipe_Message = API_Pipe_Message(sender=server_proc_def, dest=manager.node_proc.name,
        #                                          type=PipeMessageType.PIPE_REGISTER,
        #                                          body=pipe, scope=PipeEntityType.NODE)
        global node
        node.register_pipe(pipe)
        # await manager.register_pipe(pipe)
        # await manager.node_connection.send_json(msg.dict())
        return API_Response(success=True, data=server_proc_def.dict())
    except Exception as e:
        return API_Response(success=False, text=f"Error registering pipe")


@fast_api.post("/push_q")
async def push_q(q: str = Form(...), frame_file: UploadFile = Form(...)):
    q = API_Queue(**json.loads(q))
    contents = await frame_file.read()
    frame = pickle.loads(contents)
    added = await node.push_q(q, frame)
    return API_Response(success=added)


@fast_api.on_event("startup")
async def startup_event():
    global node
    print("network ready")
    node.start()
    print("Server ready")
    return


async def handle_server_message(message: API_Pipe_Message):
    pass


msg_counter = 0


@fast_api.websocket("/ws/connect/{proc_name}")
async def websocket_endpoint(websocket: WebSocket, proc_name: str):
    global msg_counter
    await node.connect_proc(proc_name, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_counter += 1
            try:
                proc_msg: API_Pipe_Message = parse_pipe_message(json.loads(data))
                if proc_msg.scope == PipeEntityType.SERVER:
                    await handle_server_message(msg)
                else:
                    node.process_message(proc_msg)
            except Exception as e:
                raise ValueError("Un supported processor message")
    except WebSocketDisconnect:
        await node.disconnect_proc(proc_name, websocket)
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
