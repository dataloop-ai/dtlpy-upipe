from pydantic import BaseModel
from pydantic.class_validators import Optional

node_server = None


class HW_Usage(BaseModel):
    cpu: float
    memory: float
