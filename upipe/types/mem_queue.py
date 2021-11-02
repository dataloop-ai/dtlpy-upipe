from pydantic import BaseModel
from pydantic.annotated_types import Dict
from pydantic.class_validators import Optional

from .base import APIPipeEntity, PipeEntityType


class APIQueue(APIPipeEntity):
    type: PipeEntityType = PipeEntityType.QUEUE
    from_p: str
    to_p: str
    size: int
    host: Optional[str]


class APIProcQueues(BaseModel):
    proc_name: str
    queues: Dict[str, APIQueue] = {}
