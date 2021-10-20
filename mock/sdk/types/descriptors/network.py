from pydantic import BaseModel
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
    path: str
    pid: int
    controller: bool


class API_Response(BaseModel):
    success: bool
    code: Optional[str]
    message: Optional[str]
    data: Optional[dict]
