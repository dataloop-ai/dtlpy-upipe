from pydantic import BaseModel
from pydantic.class_validators import Optional

node_server = None


class UtilizationEntry(BaseModel):
    cpu: float
    memory: float
    pending: int
    time: int


class QStatus(BaseModel):
    q_id: str
    pending: int
    time: int
