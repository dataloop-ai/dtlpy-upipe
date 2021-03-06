from pydantic import BaseModel
from pydantic.annotated_types import Dict
from pydantic.class_validators import Optional

from .base import UPipeEntity, UPipeEntityType


class APIQueue(UPipeEntity):
    type: UPipeEntityType = UPipeEntityType.QUEUE
    from_p: str
    to_p: str
    size: int
    host: Optional[str]


class APIProcQueues(BaseModel):
    proc_id: str
    queues: Dict[str, APIQueue] = {}
