from enum import IntEnum
from pydantic import BaseModel
from pydantic.class_validators import Optional

from .base import PipeEntityType


class PipeMessageType(IntEnum):
    Q_STATUS = 1
    Q_UPDATE = 2
    PROC_REGISTER = 3
    PROC_TERMINATE = 4
    PIPE_REGISTER = 5
    NODE_INIT = 6
    PIPE_CONTROL = 7
    PIPE_STATUS = 8
    CONFIG_UPDATE = 9
    REGISTRATION_INFO = 10


class APIPipeMessage(BaseModel):
    dest: str
    type: PipeMessageType
    sender: str
    scope: PipeEntityType
    body: Optional[dict]

    @staticmethod
    def from_json(json: dict):
        return APIPipeMessage.parse_obj(json)
