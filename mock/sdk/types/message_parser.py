from .messages import API_Pipe_Message, PipeEntityType, PipeMessageType
from .pipe import API_Pipe_Control_Message, API_Pipe_Status_Message


def parse_pipe_message(json: API_Pipe_Message):
    msg: API_Pipe_Message = API_Pipe_Message.parse_obj(json)
    if msg.type == PipeMessageType.PIPE_CONTROL:
        return API_Pipe_Control_Message.parse_obj(json)
    if msg.type == PipeMessageType.PIPE_STATUS:
        return API_Pipe_Status_Message.parse_obj(json)
    return msg
