from enum import IntEnum

from pydantic.class_validators import Optional

from . import APIProcessor, UPipeMessage
from .base import UPipeEntityType, UPipeEntity


class ProcessorExecutionStatus(IntEnum):
    INIT = 1
    READY = 3
    PAUSED = 4
    RUNNING = 5
    COMPLETED = 6
    PENDING_TERMINATION = 7

class ProcessorInstanceAction(IntEnum):
    REQUEST_TERMINATION = 1


class APIProcessorInstance(UPipeEntity):
    pid: str


class APIProcess(APIProcessor):
    instance_id: int
    pid: Optional[int]
    type: UPipeEntityType = UPipeEntityType.PROCESS


class APIInstanceActionMessage(UPipeMessage):
    action: ProcessorInstanceAction

    @staticmethod
    def from_json(json: dict):
        return APIInstanceActionMessage.parse_obj(json)
