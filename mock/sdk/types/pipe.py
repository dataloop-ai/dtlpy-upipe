from enum import IntEnum

from pydantic import BaseModel
from pydantic.annotated_types import Dict

from .messages import API_Pipe_Message, PipeMessageType
from .processor import API_Processor
from .mem_queue import API_Queue
from .base import API_Pipe_Entity, PipeEntityType


class PipeExecutionStatus(IntEnum):
    INIT = 1
    REGISTERED = 2
    READY = 3
    PAUSED = 4
    RUNNING = 5
    COMPLETED = 6


class PipeActionType(IntEnum):
    START = 1


class API_Pipe(API_Pipe_Entity):
    name: str
    processors: Dict[str, API_Processor] = {}
    queues: Dict[str, API_Queue] = {}
    type: PipeEntityType = PipeEntityType.PIPELINE


class API_Pipe_Control_Message(API_Pipe_Message):
    pipe_name: str
    action: PipeActionType

    @staticmethod
    def from_json(json: dict):
        return API_Pipe_Control_Message.parse_obj(json)


class API_Pipe_Status_Message(API_Pipe_Message):
    pipe_name: str
    status: PipeExecutionStatus

    @staticmethod
    def from_json(json: dict):
        return API_Pipe_Status_Message.parse_obj(json)


