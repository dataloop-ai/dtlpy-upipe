import asyncio
import atexit
import hashlib
import json
import os
import sys
import time
from enum import IntEnum
from threading import Thread
from typing import List

from aiohttp import ClientConnectorError
from colorama import init, Fore

from .. import node, types, entities
from ..types import UPipeEntityType, UPipeMessage, SINK_QUEUE_ID, ProcessPerformanceStats
from ..types.performance import PerformanceMetric, ThroughputPerformanceMetric

init(autoreset=True)


class ProcessorExecutionStatus(IntEnum):
    READY = 1
    PAUSED = 2
    RUNNING = 3


class Process:
    ...
    next_serial = 0
    in_qs: List[entities.MemQueue]
    out_qs: List[entities.MemQueue]
    SHARED_MEM_SIZE = 64

    def __init__(self,
                 name=None,
                 entry=None,
                 func=None,
                 settings: types.APIProcSettings = types.APIProcSettings(),
                 config: dict = None):  # name is unique per pipe

        self.instance_id = -1
        self.settings = settings
        if not name:
            name = os.environ['UPIPE_PROCESS_NAME']
        if not name:
            print(f"Warning:Nameless processor started:{name}")
        self.input_buffer_size = settings.input_buffer_size
        self.host = settings.host
        self.autoscale = settings.autoscale
        self.in_qs = []
        self.out_qs = []
        self.sink_q = None
        self.serial = None
        self.registered = False
        self.connected = False
        self.controller = False
        self.proc = None
        self.entry = entry
        self.function = None
        self.registered = False
        if config is None:
            config = dict()
        self.config = config
        if callable(func):
            self.function = func.__name__
            if entry:
                raise ChildProcessError("function can not be used with entry")
            self.entry = os.path.abspath(sys.modules['__main__'].__file__)  # main file
        self.on_frame_callback = None
        self.name = name
        self.pid = os.getpid()
        self.exe_name = os.path.basename(os.path.abspath(sys.modules['__main__'].__file__))
        self.proc_id = f"{self.name}:{self.pid}"
        self.execution_status = ProcessorExecutionStatus.RUNNING
        self.consumer_next_q_index = 0
        self.processed_counter = 0
        self.received_counter = 0
        self.dfps_in = 0
        self.dfps_out = 0
        self.last_dfps_calc_time = 0
        self.last_dfps_processed_counter = 0
        self.last_dfps_received_counter = 0
        self.interpreter = sys.executable
        self.request_termination = False  # called from manager to notify its over
        self.type = types.UPipeEntityType.PROCESS
        self.node_client = node.NodeClient(self.process_def, self.id, self._on_ws_message)
        self.current_pipe_execution_id = None
        atexit.register(self._cleanup)

    # noinspection PyBroadException
    def _cleanup(self):
        print(Fore.BLUE + f"Processor cleanup : {self.name}")
        loop = asyncio.get_event_loop()
        # try:
        #     for task in asyncio.all_tasks():
        #         task.cancel()
        # except Exception as e:
        #     print(Fore.RED + f"FAILED CLEANUP : {self.name}: {str(e)}")

        loop.run_until_complete(self.node_client.cleanup())
        print(Fore.RED + f'Bye {self.name}')

    def _add_in_q(self, q):
        self.in_qs.append(q)

    def _add_out_q(self, q):
        self.out_qs.append(q)

    async def _register(self):
        printed = False
        while True:
            try:
                (data, messages) = await self.node_client.register_proc(self.process_def)
                break
            except ClientConnectorError:
                if not printed:
                    print("Waiting for node controller ...")
                    printed = True
                await asyncio.sleep(5)
        if data['config']:
            self.config = data['config']
        for m in messages:
            message = types.UPipeMessage.parse_obj(m)
            self._handle_processor_message(message)
        self.registered = True
        return self.registered

    def start(self):
        raise NotImplementedError("Processor can not started directly")

    async def join(self):
        await self._register()
        if not self.connected:
            self.connected = self.node_client.connect()
        thread = Thread(target=self._monitor, daemon=True)
        thread.start()

    def _calc_dfps(self):
        current_time_sec = time.time()
        if self.last_dfps_calc_time == 0:
            self.last_dfps_calc_time = current_time_sec
            self.last_dfps_received_counter = self.received_counter
            self.last_dfps_processed_counter = self.processed_counter
            return
        delta_sec = current_time_sec - self.last_dfps_calc_time
        self.dfps_in = (self.received_counter - self.last_dfps_received_counter) / delta_sec
        self.dfps_out = (self.processed_counter - self.last_dfps_processed_counter) / delta_sec
        self.last_dfps_received_counter = self.received_counter
        self.last_dfps_processed_counter = self.processed_counter
        self.last_dfps_calc_time = current_time_sec
        return

    def get_stats(self):
        return ProcessPerformanceStats(dfps_in=ThroughputPerformanceMetric(value=self.dfps_in),
                                       dfps_out=ThroughputPerformanceMetric(value=self.dfps_out),
                                       received_counter=PerformanceMetric(value=self.received_counter),
                                       processed_counter=PerformanceMetric(value=self.processed_counter),
                                       pid=os.getpid())

    def _monitor(self):
        while True:
            try:
                time.sleep(1)
                self._calc_dfps()
                msg = types.ProcessStatsMessage(dest=self.process_def.id,
                                                type=types.UPipeMessageType.PROCESS_STATUS,
                                                sender=self.id,
                                                scope=types.UPipeEntityType.PROCESSOR,
                                                pid=os.getpid(),
                                                stats=self.get_stats()
                                                )
                self.node_client.send_message(msg)
                if not self.connected:
                    continue
            except Exception as e:
                print(f"Error on process monitor:{e}")

    def _in_q_exist(self, qid):
        qs = self.in_qs
        for q in qs:
            if q.id == qid:
                return True
        return False

    def _out_q_exist(self, qid):
        qs = self.out_qs
        for q in qs:
            if q.id == qid:
                return True
        return False

    def _q_exist(self, q: types.APIQueue):
        return self._in_q_exist(q.id) or self._out_q_exist(q.id)

    def _add_q(self, q: types.APIQueue):
        if q.id == SINK_QUEUE_ID:
            self.sink_q = entities.MemQueue(q)
            return
        if self._q_exist(q):
            raise BrokenPipeError(f"Q already added to proc {self.id}")
        if q.to_p == self.id and not self._in_q_exist(q.id):
            self.in_qs.append(entities.MemQueue(q))
        if q.from_p == self.id and not self._out_q_exist(q.id):
            self.out_qs.append(entities.MemQueue(q))

    def _run(self):
        self.execution_status = ProcessorExecutionStatus.RUNNING

    def _handle_intra_proc_message(self, msg):
        if msg['control'] == 'run':
            self._run()

    def _handle_processor_message(self, msg_json):
        try:
            msg = types.UPipeMessage.parse_obj(msg_json)
            if msg.type == types.UPipeMessageType.Q_UPDATE:
                print("Updating queues")
                qs = types.APIProcQueues.parse_obj(msg.body)
                for q in qs.queues:
                    queue = qs.queues[q]
                    self._add_q(queue)
            if msg.type == types.UPipeMessageType.CONFIG_UPDATE:
                print("Updating config")
                self.config = msg.body
            if msg.type == types.UPipeMessageType.REGISTRATION_INFO:
                print("Updating registration info")
                self.instance_id = msg.body['instance_id']
            if msg.type == types.UPipeMessageType.REQUEST_TERMINATION:
                print("Termination request")
                self.request_termination = True
        except Exception as e:
            print(f"Error on process message:{e}")

    def _on_ws_message(self, msg: UPipeMessage):
        if msg.scope == UPipeEntityType.PROCESSOR:
            self._handle_processor_message(msg)

    def _get_next_q_to_emit(self):
        if len(self.out_qs) == 0:
            return False
        q = self.out_qs[0]
        return q

    async def _enqueue(self, q, frame):
        if q.host:
            added = await self.node_client.put_q(q, frame)
        else:
            added = await q.put(frame)
        if not added:
            return False
        return True

    async def emit(self, data, d_type: entities.DType = None):
        if isinstance(data, entities.DataFrame):
            frame = data
        else:
            frame = entities.DataFrame(data)
        if self.current_pipe_execution_id:
            frame.set_pipe_exe_id(self.current_pipe_execution_id)
        q = self._get_next_q_to_emit()
        if not q and self.sink_q:
            sink_result = await self._enqueue(self.sink_q, frame)
            if sink_result:
                self.processed_counter += 1
            return sink_result
        if not q:
            print(f"Warning:Processor {self.name} emit dropped: No destination")
            return False
        success = True
        self.processed_counter += 1
        for q in self.out_qs:
            success = success and await self._enqueue(q, frame)
        return success

    async def emit_sync(self, data, d_type: entities.DType = None):
        if isinstance(data, entities.DataFrame):
            frame = data
        else:
            frame = entities.DataFrame(data)
        while not await self.out_qs[0].space_available(frame):
            await asyncio.sleep(.1)
        return await self.emit(data)

    async def get(self):
        sys.stdout.flush()
        for i in range(len(self.in_qs)):
            next_index = (self.consumer_next_q_index + i) % len(self.in_qs)
            q: entities.MemQueue = self.in_qs[next_index]
            frame = await q.get()
            if frame:
                self.consumer_next_q_index += 1
                if frame.pipe_execution_id:
                    self.current_pipe_execution_id = frame.pipe_execution_id
                else:
                    self.current_pipe_execution_id = None
                self.received_counter += 1
                return frame.data
        if self.request_termination:  # no more messages and goodbye requested from pipe
            await self.terminate()
        return None

    async def get_sync(self, timeout: int = 5):
        start_time = time.time()
        sleep_time = 0.01
        while True:
            data = await self.get()
            if data is not None:
                return data
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"get_sync timeout {elapsed} sec")
            await asyncio.sleep(sleep_time)

    async def terminate(self):
        (data, messages) = await self.node_client.notify_termination(self.process_def)
        sys.exit(0)

    @property
    def config_hash(self):
        if len(self.config) == 0:
            return None
        config_md5 = hashlib.md5(json.dumps(self.config, sort_keys=True).encode('utf-8')).hexdigest()
        return config_md5

    @property
    def id(self):
        if not self.config_hash:
            return f"{self.name}"
        return f"{self.name}:{self.config_hash}"

    @property
    def executable(self):
        return sys.argv[0]

    @property
    def process_def(self):
        return types.APIProcess(id=self.id,
                                name=self.name,
                                instance_id=self.instance_id,
                                pid=self.pid)
