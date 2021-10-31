import pydantic
from pydantic.class_validators import Optional
from pydantic.fields import List
from .messages import API_Pipe_Message

# noinspection PyTypeChecker
class API_Response(pydantic.BaseModel):
    success: bool
    code: Optional[str]
    messages: List[API_Pipe_Message] = []
    data: Optional[dict]
    text: Optional[str]
