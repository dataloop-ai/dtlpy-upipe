from .messages import UPipeMessage, UPipeMessageType
from .pipe import APIPipeControlMessage, APIPipeStatusMessage


def parse_pipe_message(json: UPipeMessage):
    msg: UPipeMessage = UPipeMessage.parse_obj(json)
    if msg.type == UPipeMessageType.PIPE_CONTROL:
        return APIPipeControlMessage.parse_obj(json)
    if msg.type == UPipeMessageType.PIPE_STATUS:
        return APIPipeStatusMessage.parse_obj(json)
    return msg
