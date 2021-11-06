from pydantic import BaseModel
from pydantic.class_validators import Optional
from .base import PipeEntityType, APIPipeEntity


class APIProcSettings(BaseModel):
    priority: int = 1
    autoscale: int = 1
    input_buffer_size: int = 1000 * 4096  # 1000 mem pages by default
    host: Optional[str] = None


class APIProcessor(APIPipeEntity):
    type: PipeEntityType = PipeEntityType.PROCESSOR
    entry: Optional[str]
    function: Optional[str]
    interpreter: Optional[str]
    settings: APIProcSettings = APIProcSettings()

    class Config:
        arbitrary_types_allowed = True


class APIProcessorInstance(APIPipeEntity):
    processor_id: str


class APIProcess(APIProcessor):
    instance_id: int
    pid: Optional[int]
    type: PipeEntityType = PipeEntityType.PROCESS
