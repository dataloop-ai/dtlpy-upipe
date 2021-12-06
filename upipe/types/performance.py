from pydantic import BaseModel
from pydantic.class_validators import Optional

from . import UPipeEntity

node_server = None


class NodeUtilizationEntry(BaseModel):
    cpu: float
    memory: float


class ProcUtilizationEntry(BaseModel):
    cpu: float
    memory: float
    pending: Optional[int]
    time: int
    proc: UPipeEntity


class QStatus(BaseModel):
    q_id: str
    pending: int
    time: int
