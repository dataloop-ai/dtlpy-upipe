from .messages import APIPipeMessage, PipeMessageType
from .pipe import APIPipeControlMessage, APIPipeStatusMessage


def parse_pipe_message(json: APIPipeMessage):
    msg: APIPipeMessage = APIPipeMessage.parse_obj(json)
    if msg.type == PipeMessageType.PIPE_CONTROL:
        return APIPipeControlMessage.parse_obj(json)
    if msg.type == PipeMessageType.PIPE_STATUS:
        return APIPipeStatusMessage.parse_obj(json)
    return msg
