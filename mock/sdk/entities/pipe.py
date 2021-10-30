import asyncio

from .processor import Processor
from .. import API_Pipe, API_Queue, PipeActionType, API_Proc_Message, \
    ProcMessageType, API_Pipe_Status_Message, PipeExecutionStatus, API_Pipe_Control_Message, ProcType, API_Proc
from mock import wait_for_node_ready, start_server

control_mem_name = "control_mem"


class Pipe(Processor):

    def __init__(self, name):
        Processor.__init__(self, name)
        self._completion_future: asyncio.Future = asyncio.Future()
        self._start_future: asyncio.Future = asyncio.Future()
        self.server_proc = None
        # self.main_block = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    def handle_message(self, msg: API_Proc_Message):
        super().handle_message(msg)
        if msg.type == ProcMessageType.PIPE_STATUS:
            msg = API_Pipe_Status_Message(msg)
            if msg.status == PipeExecutionStatus.COMPLETED:
                self._completion_future.set_result(0)
            if msg.status == PipeExecutionStatus.RUNNING:
                self._start_future.set_result(0)

    def send_pipe_action(self, action: PipeActionType):
        msg = API_Pipe_Control_Message(dest=self.name, type=ProcMessageType.PIPE_CONTROL,
                                       sender=self.api_def,
                                       action=action, pipe_name=self.name, scope=ProcType.PIPELINE)
        self.node_client.send_message(msg)

    async def register(self):
        proc, messages = await self.node_client.register_pipe(self.pipe_def)
        self.server_proc = API_Proc.parse_obj(proc)
        return self.server_proc

    async def start(self):
        start_server()
        print(f"Starting pipe {self.name}")
        if not await self.register():
            raise BrokenPipeError(f"Cant register pipe : {self.name}")
        print(f"{self.name} Registered")
        if not self.node_client.connect():
            raise BrokenPipeError(f"Cant connect pipe : {self.name}")
        print(f"Pipe {self.name} ready")
        self.send_pipe_action(PipeActionType.START)
        self._start_future = asyncio.Future()
        self._completion_future = asyncio.Future()
        await asyncio.wait([self._start_future])
        print(f"{self.name} running")

    async def wait_for_completion(self):
        if not self._completion_future:
            return
        await asyncio.wait([self._completion_future])
        # self.cleanup()

    @property
    def pipe_def(self):
        pipe_api_def = API_Pipe(name=self.name)

        def map_proc(processor: Processor):
            pipe_api_def.processors[processor.name] = processor.api_def
            for child in processor.children:
                qid = f"{processor.name}:{child.name}"
                host = None
                if child.api_def.settings.host:
                    host = child.api_def.settings.host
                q_def = API_Queue(qid=qid, from_p=processor.name, to_p=child.name, size=child.input_buffer_size,
                                  host=host)
                pipe_api_def.queues[qid] = q_def
                map_proc(child)

        map_proc(self)
        return pipe_api_def
