from pydantic import BaseModel
from pydantic.annotated_types import Dict
from pydantic.class_validators import Optional

from .base import API_Pipe_Entity, PipeEntityType


class API_Queue(API_Pipe_Entity):
    type: PipeEntityType = PipeEntityType.QUEUE
    from_p: str
    to_p: str
    size: int
    host: Optional[str]


class API_Proc_Queues(BaseModel):
    proc_name: str
    queues: Dict[str, API_Queue] = {}
