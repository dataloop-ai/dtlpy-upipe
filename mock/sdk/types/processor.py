from pydantic import BaseModel
from pydantic.class_validators import Optional
from .base import PipeEntityType, API_Pipe_Entity


class API_ProcSettings(BaseModel):
    priority: int = 1
    autoscale: int = 1
    input_buffer_size: int = 1000 * 4096  # 1000 mem pages by default
    host: Optional[str] = None


class API_Processor(API_Pipe_Entity):

    type: PipeEntityType = PipeEntityType.PROCESSOR
    entry: Optional[str]
    function: Optional[str]
    interpreter: Optional[str]
    settings: API_ProcSettings = API_ProcSettings()

    class Config:
        arbitrary_types_allowed = True

class API_Processor_Instance(API_Pipe_Entity):
    processor_id: str

class API_Process(API_Processor):
    instance_id: int
    pid: Optional[int]
    type: PipeEntityType = PipeEntityType.PROCESS
