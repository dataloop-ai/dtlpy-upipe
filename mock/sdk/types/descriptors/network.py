from enum import IntEnum

from pydantic import BaseModel
from pydantic.annotated_types import Dict
from pydantic.class_validators import Optional
from pydantic.fields import List


class API_Queue(BaseModel):
    from_p: str
    to_p: str
    qid: str
    size: int
    host: Optional[str]


class API_NodeSettings(BaseModel):
    name: str = "main_node"


class API_ProcSettings(BaseModel):
    priority: int = 1
    autoscale: int = 1
    input_buffer_size: int = 1000 * 4096  # 1000 mem pages by default
    host: Optional[str] = None


class ProcType(IntEnum):
    PROCESSOR = 1
    PROCESSOR_CONTROLLER = 2
    PIPELINE = 3
    PIPELINE_CONTROLLER = 4
    SERVER = 5
    NODE = 6


class API_Proc(BaseModel):
    name: str
    type: ProcType
    entry: Optional[str]
    function: Optional[str]
    interpreter: Optional[str]
    settings: API_ProcSettings = API_ProcSettings()
    config: dict = {}

    class Config:
        arbitrary_types_allowed = True


class API_Proc_Queues(BaseModel):
    proc_name: str
    queues: Dict[str, API_Queue] = {}


server_proc_def = API_Proc(name="upipe-local-server", type=ProcType.SERVER)


class API_Pipe(BaseModel):
    name: str
    processors: Dict[str, API_Proc] = {}
    queues: Dict[str, API_Queue] = {}


class API_Proc_Instance(API_Proc):
    instance_id: int
    pid: Optional[int]


class ProcMessageType(IntEnum):
    Q_STATUS = 1
    Q_UPDATE = 2
    PROC_REGISTER = 3
    PROC_TERMINATE = 4
    PIPE_REGISTER = 5
    NODE_INIT = 6
    PIPE_CONTROL = 7
    PIPE_STATUS = 8
    CONFIG_UPDATE = 9
    REGISTRATION_INFO = 10


class PipeActionType(IntEnum):
    START = 1


class PipeExecutionStatus(IntEnum):
    INIT = 1
    REGISTERED = 2
    READY = 3
    PAUSED = 4
    RUNNING = 5
    COMPLETED = 6


class API_Proc_Message(BaseModel):
    dest: str
    type: ProcMessageType
    sender: API_Proc
    scope: ProcType
    body: Optional[dict]

    @staticmethod
    def from_json(json: dict):
        if json['type'] == ProcMessageType.PIPE_CONTROL:
            return API_Pipe_Control_Message.parse_obj(json)
        if json['type'] == ProcMessageType.PIPE_STATUS:
            return API_Pipe_Status_Message.parse_obj(json)
        return API_Proc_Message.parse_obj(json)


class API_Pipe_Control_Message(API_Proc_Message):
    pipe_name: str
    action: PipeActionType


class API_Pipe_Status_Message(API_Proc_Message):
    pipe_name: str
    status: PipeExecutionStatus


class API_Node(BaseModel):
    name: str
    host_name: str
    id: str


# noinspection PyTypeChecker
class API_Response(BaseModel):
    success: bool
    code: Optional[str]
    messages: List[API_Proc_Message] = []
    data: Optional[dict]
    text: Optional[str]
