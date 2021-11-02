from pydantic import BaseModel
from pydantic.class_validators import Optional

from . import APIPipeEntity

node_server = None


class NodeUtilizationEntry(BaseModel):
    cpu: float
    memory: float


class ProcUtilizationEntry(BaseModel):
    cpu: float
    memory: float
    pending: Optional[int]
    time: int
    proc: APIPipeEntity


class QStatus(BaseModel):
    q_id: str
    pending: int
    time: int
