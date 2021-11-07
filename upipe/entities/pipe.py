import asyncio

from .processor import Processor
from .. import types, node

control_mem_name = "control_mem"


class Pipe(Processor):

    def __init__(self, name):
        Processor.__init__(self, name)
        self._completion_future: asyncio.Future = asyncio.Future()
        self._start_future: asyncio.Future = asyncio.Future()
        self.server_proc = None
        # self.main_block = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    def handle_pipelines_message(self, msg_json):
        msg = types.APIPipeMessage.parse_obj(msg_json)
        if msg.type == types.PipeMessageType.PIPE_STATUS:
            status_msg = types.APIPipeStatusMessage.parse_obj(msg_json)
            if status_msg.status == types.PipeExecutionStatus.COMPLETED:
                self._completion_future.set_result(0)
            if status_msg.status == types.PipeExecutionStatus.RUNNING:
                self._start_future.set_result(0)

    def send_pipe_action(self, action: types.PipeActionType):
        msg = types.APIPipeControlMessage(dest=self.name,
                                          type=types.PipeMessageType.PIPE_CONTROL,
                                          sender=self.processor_def.id,
                                          action=action,
                                          pipe_name=self.name,
                                          scope=types.PipeEntityType.PIPELINE)
        self.node_client.send_message(msg)

    async def register(self):
        proc, messages = await self.node_client.register_pipe(self.pipe_def)
        self.server_proc = types.APIPipeEntity.parse_obj(proc)
        return self.server_proc

    async def start(self):
        node.start_server()
        print(f"Starting pipe {self.name}")
        if not await self.register():
            raise BrokenPipeError(f"Cant register pipe : {self.name}")
        print(f"{self.name} Registered")
        if not self.node_client.connect():
            raise BrokenPipeError(f"Cant connect pipe : {self.name}")
        print(f"Pipe {self.name} pending execution")
        self.send_pipe_action(types.PipeActionType.START)
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
    def id(self):
        return self.name

    @property
    def pipe_def(self):
        pipe_api_def = types.APIPipe(name=self.name, id=self.name)

        def map_proc(processor: Processor):
            proc_def = processor.processor_def
            pipe_api_def.processors[proc_def.name] = proc_def
            for child in processor.children:
                qid = f"{processor.name}:{child.name}"
                host = None
                if child.processor_def.settings.host:
                    host = child.processor_def.settings.host
                q_def = types.APIQueue(id=qid, name=qid, from_p=processor.name, to_p=child.name,
                                       size=child.input_buffer_size,
                                       host=host)
                pipe_api_def.queues[qid] = q_def
                map_proc(child)

        map_proc(self)
        return pipe_api_def
