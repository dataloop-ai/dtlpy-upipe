from pydantic import BaseModel


from .network import API_Proc

node_server = None

class NodeUtilizationEntry(BaseModel):
    cpu: float
    memory: float

class ProcUtilizationEntry(BaseModel):
    cpu: float
    memory: float
    pending: int
    time: int
    proc: API_Proc


class QStatus(BaseModel):
    q_id: str
    pending: int
    time: int
