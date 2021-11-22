from enum import IntEnum
from pydantic.annotated_types import Dict

from .messages import APIPipeMessage
from .processor import APIProcessor
from .mem_queue import APIQueue
from .base import APIPipeEntity, PipeEntityType


class PipeExecutionStatus(IntEnum):
    INIT = 1
    REGISTERED = 2
    READY = 3
    PAUSED = 4
    RUNNING = 5
    COMPLETED = 6


class PipeActionType(IntEnum):
    START = 1


class APIPipe(APIPipeEntity):
    name: str
    processors: Dict[str, APIProcessor] = {}
    queues: Dict[str, APIQueue] = {}
    type: PipeEntityType = PipeEntityType.PIPELINE


class APIPipeControlMessage(APIPipeMessage):
    pipe_name: str
    action: PipeActionType

    @staticmethod
    def from_json(json: dict):
        return APIPipeControlMessage.parse_obj(json)


class APIPipeStatusMessage(APIPipeMessage):
    pipe_name: str
    status: PipeExecutionStatus

    @staticmethod
    def from_json(json: dict):
        return APIPipeStatusMessage.parse_obj(json)
