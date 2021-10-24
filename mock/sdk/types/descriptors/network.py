from enum import IntEnum

from pydantic import BaseModel, typing
from pydantic.class_validators import Optional
from pydantic.fields import List

node_server = None
NODE_PROC_NAME = "up_node_manager"

class API_Queue(BaseModel):
    from_p: str
    to_p: str
    q_id: int
    size: int
    host: Optional[str]


class API_Proc(BaseModel):
    name: str
    entry: Optional[str]
    function: Optional[str]
    interpreter: Optional[str]
    controller: bool
    autoscale: int = 1


class API_Proc_Instance(API_Proc):
    instance_id: int
    pid: int

class ProcMessageType(IntEnum):
    Q_STATUS = 1
    Q_UPDATE = 2
    PROC_REGISTER = 3
    PROC_TERMINATE = 4

class API_Proc_Message(BaseModel):
    dest: str
    type: ProcMessageType
    sender: API_Proc
    body: Optional[dict]


class API_Node(BaseModel):
    name: str
    host_name: str
    id: str


class API_Response(BaseModel):
    success: bool
    code: Optional[str]
    messages: Optional[List[API_Proc_Message]] = []
    data: Optional[dict]
