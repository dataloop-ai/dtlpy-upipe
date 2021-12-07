from enum import IntEnum
from pydantic.annotated_types import Dict

from .messages import UPipeMessage
from .processor import APIProcessor

from .mem_queue import APIQueue
from .base import UPipeEntityType, UPipeEntity

class PipeExecutionStatus(IntEnum):
    INIT = 1
    REGISTERED = 2
    READY = 3
    PAUSED = 4
    RUNNING = 5
    COMPLETED = 6


class PipeActionType(IntEnum):
    START = 1
    RESTART = 2
    PAUSE = 3


class APIPipe(UPipeEntity):
    name: str
    processors: Dict[str, APIProcessor] = {}
    queues: Dict[str, APIQueue] = {}
    type: UPipeEntityType = UPipeEntityType.PIPELINE


class APIPipeControlMessage(UPipeMessage):
    pipe_name: str
    action: PipeActionType

    @staticmethod
    def from_json(json: dict):
        return APIPipeControlMessage.parse_obj(json)


class APIPipeStatusMessage(UPipeMessage):
    pipe_name: str
    status: PipeExecutionStatus

    @staticmethod
    def from_json(json: dict):
        return APIPipeStatusMessage.parse_obj(json)


class PipelineAlreadyExist(Exception):
    def __init__(self, pipeline_id: str, message=f"Pipeline already exist"):
        self.pipeline_id = pipeline_id
        self.message = message=f"Pipeline {pipeline_id} already exist"
        super().__init__(self.message)
