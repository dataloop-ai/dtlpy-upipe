from pydantic import BaseModel
from .base import API_Pipe_Entity

class API_Node(API_Pipe_Entity):
    controller: bool
    controller_host: str = None
    controller_port: int = None
    id: str
