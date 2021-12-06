from enum import IntEnum

from pydantic import BaseModel
from pydantic.class_validators import Optional
from .base import UPipeEntityType, UPipeEntity


class ProcessorExecutionStatus(IntEnum):
    INIT = 1
    READY = 3
    PAUSED = 4
    RUNNING = 5
    COMPLETED = 6

class APIProcSettings(BaseModel):
    priority: int = 1
    autoscale: int = 1
    input_buffer_size: int = 1000 * 4096  # 1000 mem pages by default
    host: Optional[str] = None


class APIProcessor(UPipeEntity):
    type: UPipeEntityType = UPipeEntityType.PROCESSOR
    entry: Optional[str]
    function: Optional[str]
    interpreter: Optional[str]
    settings: APIProcSettings = APIProcSettings()

    class Config:
        arbitrary_types_allowed = True


class APIProcessorInstance(UPipeEntity):
    pid: str


class APIProcess(APIProcessor):
    instance_id: int
    pid: Optional[int]
    type: UPipeEntityType = UPipeEntityType.PROCESS
