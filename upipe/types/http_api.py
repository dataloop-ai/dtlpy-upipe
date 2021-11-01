import pydantic
from pydantic.class_validators import Optional
from pydantic.fields import List

from .messages import APIPipeMessage


class APIResponse(pydantic.BaseModel):
    success: bool
    code: Optional[str]
    messages: List[APIPipeMessage] = list()
    data: Optional[dict]
    text: Optional[str]
