import asyncio
import time
from typing import Dict

from .processor import Processor
from .worker import Worker
from .. import types, node, entities
from ..types import APIQueue, SINK_QUEUE_ID, UPipeMessage

control_mem_name = "control_mem"


class PipeFrameFuture(asyncio.Future):
    def __init__(self, timeout_ms=1000):
        super().__init__()
        self.created_time_ms = time.time() * 1000
        self.timeout_ms = timeout_ms


class Pipe(Processor, Worker):

    def __init__(self, name):
        Processor.__init__(self, name)
        Worker.__init__(self, name)
        self.type = types.UPipeEntityType.PIPELINE
        self.node_client = node.NodeClient(self.processor_def, name, self._on_ws_message)
        self._completion_future: asyncio.Future = asyncio.Future()
        self._start_future: asyncio.Future = asyncio.Future()
        self.server_proc = None
        self.status: types.PipeExecutionStatus = types.PipeExecutionStatus.INIT
        self.sink_q = entities.MemQueue(self.pipe_def.sink)
        self.executing_frames: Dict[str, PipeFrameFuture] = dict()
        self.process = Worker(name=self.name)
        self.out_qs = []
        self.out_qs_defs = []
        self.loaded = False
        # self.main_block = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    def _handle_pipelines_message(self, msg_json):
        msg = types.UPipeMessage.parse_obj(msg_json)
        if msg.type == types.UPipeMessageType.PIPE_STATUS:
            status_msg = types.APIPipeStatusMessage.parse_obj(msg_json)
            self.status = status_msg.status
            if status_msg.status == types.PipeExecutionStatus.COMPLETED:
                self._completion_future.set_result(0)
            if status_msg.status == types.PipeExecutionStatus.RUNNING:
                self._start_future.set_result(0)

    def _send_pipe_action(self, action: types.PipeActionType):
        msg = types.APIPipeControlMessage(dest=self.name,
                                          type=types.UPipeMessageType.PIPE_CONTROL,
                                          sender=self.processor_def.id,
                                          action=action,
                                          pipe_name=self.name,
                                          scope=types.UPipeEntityType.PIPELINE)
        self.node_client.send_message(msg)

    async def _load_to_server(self):
        if self.loaded:
            return True
        pipe_def = self.pipe_def
        proc, messages = await self.node_client.load_pipe(pipe_def)
        for q_id in pipe_def.queues:
            q = pipe_def.queues[q_id]
            if q.from_p == self.id:
                self.out_qs_defs.append(q)
        for pipe_q in self.out_qs_defs:
            self.out_qs.append(entities.MemQueue(pipe_q))
        self.server_proc = types.UPipeEntity.parse_obj(proc)
        self.loaded = True
        return self.server_proc

    async def load(self):
        node.start_server()
        print(f"Starting pipe {self.name}")
        if not await self._load_to_server():
            raise BrokenPipeError(f"Cant load pipe : {self.name}")
        print(f"{self.name} Registered")
        if not self.node_client.connect():
            raise BrokenPipeError(f"Cant connect pipe : {self.name}")
        loop = asyncio.get_event_loop()
        loop.create_task(self._baby_sitter())

    async def start(self):
        await self.load()
        print(f"Pipe {self.name} pending execution")
        self._send_pipe_action(types.PipeActionType.START)
        self._start_future = asyncio.Future()
        self._completion_future = asyncio.Future()
        await asyncio.wait([self._start_future])
        print(f"{self.name} running")

    async def _baby_sitter(self):
        while True:
            if self.completed:
                return
            frame = await self.sink_q.get()
            if frame:
                if frame.pipe_execution_id:
                    if frame.pipe_execution_id not in self.executing_frames:
                        raise BrokenPipeError("Completed frame not found on log")
                    self.executing_frames[frame.pipe_execution_id].set_result(frame)
                    continue
            await asyncio.sleep(0)

    @staticmethod
    def _generate_pipe_frame(data, d_type: entities.DType = None):
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
        frame = self._generate_pipe_frame(data, d_type)
        success = await super().emit(frame)
        return success

    async def emit_sync(self, data, d_type: entities.DType = None, timeout_ms=500):
        if timeout_ms < 0:
            timeout_sec = None
        else:
            timeout_sec = timeout_ms / 1000
        if self.status != types.PipeExecutionStatus.RUNNING:
            raise BrokenPipeError("Pipe is not running: data ingestion blocked")
        frame = self._generate_pipe_frame(data, d_type)
        self.executing_frames[frame.pipe_execution_id] = PipeFrameFuture()
        success = await super().emit_sync(frame)
        if success:
            await asyncio.wait([self.executing_frames[frame.pipe_execution_id]], timeout=timeout_sec)
            try:
                result: entities.DataFrame = self.executing_frames[frame.pipe_execution_id].result()
                return result.data
            except asyncio.exceptions.InvalidStateError:
                raise TimeoutError(f"Timeout : No result in {timeout_ms} ms")
        return False

    async def wait_for_completion(self):
        if not self._completion_future:
            return
        await asyncio.wait([self._completion_future])
        # self.cleanup()

    async def terminate(self, ):
        print(f"Terminating pipe {self.name}")
        self._send_pipe_action(types.PipeActionType.TERMINATE)
        self._completion_future = asyncio.Future()
        return await self.wait_for_completion()

    @property
    def id(self):
        return self.name

    def _on_ws_message(self, msg: UPipeMessage):
        self._handle_pipelines_message(msg)

    @property
    def completed(self):
        return self.status == types.PipeExecutionStatus.COMPLETED

    @property
    def pending_termination(self):
        return self.status == types.PipeExecutionStatus.PENDING_TERMINATION

    @property
    def running(self):
        return self.status == types.PipeExecutionStatus.RUNNING

    @property
    def _sink_q_def(self):
        sink: APIQueue = APIQueue(name="pipe_sink_q", from_p="*", to_p=self.processor_def.id,
                                  size=self.input_buffer_size,
                                  id=SINK_QUEUE_ID)
        return sink

    @property
    def pipe_def(self):
        pipe_api_def = types.APIPipe(name=self.name, id=self.name, root=self.processor_def, sink=self._sink_q_def)

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
