import asyncio
import time
from typing import Dict

from .processor import Processor
from .. import types, node, entities
from ..types import APIQueue, SINK_QUEUE_ID

control_mem_name = "control_mem"


class PipeFrameFuture(asyncio.Future):
    def __init__(self):
        super().__init__()
        self.created_time_ms = time.time() * 1000


class Pipe(Processor):

    def __init__(self, name):
        Processor.__init__(self, name)
        self.type = types.UPipeEntityType.PIPELINE
        self.node_client = node.NodeClient(self.processor_def, name, self.on_ws_message)
        self._completion_future: asyncio.Future = asyncio.Future()
        self._start_future: asyncio.Future = asyncio.Future()
        self.server_proc = None
        self.status: types.PipeExecutionStatus = types.PipeExecutionStatus.INIT
        self.sink_q = entities.MemQueue(self.pipe_def.sink)
        self.executing_frames: Dict[str, PipeFrameFuture] = dict()
        # self.main_block = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    def handle_pipelines_message(self, msg_json):
        msg = types.UPipeMessage.parse_obj(msg_json)
        if msg.type == types.UPipeMessageType.PIPE_STATUS:
            status_msg = types.APIPipeStatusMessage.parse_obj(msg_json)
            self.status = status_msg.status
            if status_msg.status == types.PipeExecutionStatus.COMPLETED:
                self._completion_future.set_result(0)
            if status_msg.status == types.PipeExecutionStatus.RUNNING:
                self._start_future.set_result(0)

    def send_pipe_action(self, action: types.PipeActionType):
        msg = types.APIPipeControlMessage(dest=self.name,
                                          type=types.UPipeMessageType.PIPE_CONTROL,
                                          sender=self.processor_def.id,
                                          action=action,
                                          pipe_name=self.name,
                                          scope=types.UPipeEntityType.PIPELINE)
        self.node_client.send_message(msg)

    async def load_to_server(self):
        proc, messages = await self.node_client.load_pipe(self.pipe_def)
        self.server_proc = types.UPipeEntity.parse_obj(proc)
        return self.server_proc

    async def load(self):
        node.start_server()
        print(f"Starting pipe {self.name}")
        if not await self.load_to_server():
            raise BrokenPipeError(f"Cant load pipe : {self.name}")
        print(f"{self.name} Registered")
        if not self.node_client.connect():
            raise BrokenPipeError(f"Cant connect pipe : {self.name}")

    async def start(self):
        await self.load()
        print(f"Pipe {self.name} pending execution")
        self.send_pipe_action(types.PipeActionType.START)
        self._start_future = asyncio.Future()
        self._completion_future = asyncio.Future()
        await asyncio.wait([self._start_future])
        loop = asyncio.get_event_loop()
        loop.create_task(self.baby_sitter())
        print(f"{self.name} running")

    async def baby_sitter(self):
        while self.running:
            frame = await self.sink_q.get()
            if frame:
                if frame.pipe_execution_id:
                    if frame.pipe_execution_id not in self.executing_frames:
                        raise BrokenPipeError("Completed frame not found on log")
                    self.executing_frames[frame.pipe_execution_id].set_result(frame)
                    continue
            await asyncio.sleep(.001)

    @staticmethod
    def generate_pipe_frame(data, d_type: entities.DType = None):
        if isinstance(data, entities.DataFrame):
            frame = data
        else:
            frame = entities.DataFrame(data)
        if frame.pipe_execution_id is None:
            frame.set_pipe_exe_id()
        return frame

    async def emit(self, data, d_type: entities.DType = None):
        if self.status != types.PipeExecutionStatus.RUNNING:
            raise BrokenPipeError("Pipe is not running: data ingestion blocked")
        frame = self.generate_pipe_frame(data, d_type)
        success = await super().emit(frame)
        return success

    async def emit_sync(self, data, d_type: entities.DType = None):
        if self.status != types.PipeExecutionStatus.RUNNING:
            raise BrokenPipeError("Pipe is not running: data ingestion blocked")
        frame = self.generate_pipe_frame(data, d_type)
        success = await super().emit_sync(frame)
        if success:
            self.executing_frames[frame.pipe_execution_id] = PipeFrameFuture()
            await asyncio.wait([self.executing_frames[frame.pipe_execution_id]])
            result: entities.DataFrame = self.executing_frames[frame.pipe_execution_id].result()
            return result.data
        return False

    async def wait_for_completion(self):
        if not self._completion_future:
            return
        await asyncio.wait([self._completion_future])
        # self.cleanup()

    async def terminate(self, ):
        print(f"Terminating pipe {self.name}")
        self.send_pipe_action(types.PipeActionType.TERMINATE)
        self._completion_future = asyncio.Future()
        return await self.wait_for_completion()

    @property
    def id(self):
        return self.name

    @property
    def completed(self):
        return self.status == types.PipeExecutionStatus.COMPLETED

    @property
    def running(self):
        return self.status == types.PipeExecutionStatus.RUNNING

    @property
    def pipe_def(self):
        sink: APIQueue = APIQueue(name="pipe_sink_q", from_p="*", to_p=self.processor_def.id,
                                  size=self.input_buffer_size,
                                  id=SINK_QUEUE_ID)
        pipe_api_def = types.APIPipe(name=self.name, id=self.name, root=self.processor_def, sink=sink)

        def map_proc(processor: Processor):
            proc_def = processor.processor_def
            pipe_api_def.processors[proc_def.id] = proc_def
            for child in processor.children:
                qid = f"{processor.id}->{child.id}"
                host = None
                if child.processor_def.settings.host:
                    host = child.processor_def.settings.host
                q_def = types.APIQueue(id=qid, name=qid, from_p=processor.id, to_p=child.id,
                                       size=child.input_buffer_size,
                                       host=host)
                pipe_api_def.queues[qid] = q_def
                map_proc(child)

        map_proc(self)
        return pipe_api_def
