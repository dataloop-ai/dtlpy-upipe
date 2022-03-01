import hashlib
import json
from enum import IntEnum
from pydantic import BaseModel
from pydantic.class_validators import Optional

from .base import UPipeEntityType


class UPipeMessageType(IntEnum):
    Q_STATUS = 1
    Q_UPDATE = 2
    PROC_REGISTER = 3
    REQUEST_TERMINATION = 4
    PIPE_REGISTER = 5
    NODE_INIT = 6
    PIPE_CONTROL = 7
    PIPE_STATUS = 8
    CONFIG_UPDATE = 9
    REGISTRATION_INFO = 10
    INSTANCE_ACTION = 11
    NODE_STATUS = 12
    PROCESS_STATUS = 13


class UPipeMessage(BaseModel):
    dest: str
    type: UPipeMessageType
    sender: str
    scope: UPipeEntityType
    body: Optional[dict]

    def hash(self):
        return hashlib.md5(json.dumps(self.dict()).encode('utf-8')).hexdigest()

    @staticmethod
    def from_json(json_: dict):
        return UPipeMessage.parse_obj(json_)
