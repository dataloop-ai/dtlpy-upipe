from pydantic import BaseModel, typing
from pydantic.class_validators import Optional

node_server = None


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
    autoscale: int


class API_Proc_Instance(API_Proc):
    instance_id: int
    pid: int


class API_Proc_Message(BaseModel):
    dest: str
    type: str
    proc: API_Proc
    body: dict


class API_Node(BaseModel):
    name: str
    host_name: str
    id: str


class API_Response(BaseModel):
    success: bool
    code: Optional[str]
    message: Optional[str]
    data: Optional[dict]
