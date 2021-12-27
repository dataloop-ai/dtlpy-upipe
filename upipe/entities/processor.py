import asyncio
import atexit
import hashlib
import json
import os
import sys
import time
from enum import IntEnum
from typing import List

from aiohttp import ClientConnectorError
from colorama import init, Fore

from .. import node, types, entities
from ..types import UPipeEntityType, UPipeMessage

init(autoreset=True)


class ProcessorExecutionStatus(IntEnum):
    READY = 1
    PAUSED = 2
    RUNNING = 3


class Processor:
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
            name = sys.argv[0]
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
        self.children = list()
        self.pid = os.getpid()
        self.exe_name = os.path.basename(os.path.abspath(sys.modules['__main__'].__file__))
        self.proc_id = f"{self.name}:{self.pid}"
        self.execution_status = ProcessorExecutionStatus.RUNNING
        self.consumer_next_q_index = 0
        self.interpreter = sys.executable
        self.request_termination = False  # called from manager to notify its over
        self.type = types.UPipeEntityType.PROCESSOR
        self.node_client = node.NodeClient(self.processor_def, self.id, self.on_ws_message)
        self.current_pipe_execution_id = None
        self.enqueue_counter = 0
        atexit.register(self.cleanup)

    # noinspection PyBroadException
    def cleanup(self):
        print(Fore.BLUE + f"Processor cleanup : {self.name}")
        loop = asyncio.get_event_loop()
        # try:
        #     for task in asyncio.all_tasks():
        #         task.cancel()
        # except Exception as e:
        #     print(Fore.RED + f"FAILED CLEANUP : {self.name}: {str(e)}")

        loop.run_until_complete(self.node_client.cleanup())
        print(Fore.RED + f'Bye {self.name}')

    def add_in_q(self, q):
        self.in_qs.append(q)

    def add_out_q(self, q):
        self.out_qs.append(q)

    def add(self, processor):
        if self.get_child(processor.name):
            return
        print("Adding {}".format(processor.name))
        self.children.append(processor)

        return processor

    async def register(self):
        printed = False
        while True:
            try:
                (data, messages) = await self.node_client.register_proc(self.processor_def)
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
            self.handle_processor_message(message)
        self.registered = True
        return self.registered

    def start(self):
        raise NotImplementedError("Processor can not started directly")

    async def connect(self):
        # if not self.registered:
        await self.register()
        if not self.connected:
            self.connected = self.node_client.connect()
        # thread = Thread(target=self.monitor, daemon=True)
        # thread.start()

    def get_child(self, name):
        proc = next((p for p in self.children if p.name == name), None)
        return proc

    def monitor(self):
        while True:
            time.sleep(1)
            if not self.connected:
                continue

    def all_child_procs(self):
        procs = [self]
        for p in self.children:
            procs.extend(p.all_child_procs())
        return procs

    @property
    def count(self):
        me = 0
        if self.proc:
            me = 1
        return me + sum([p.count for p in self.children])

    def in_q_exist(self, qid):
        qs = self.in_qs
        for q in qs:
            if q.id == qid:
                return True
        return False

    def out_q_exist(self, qid):
        qs = self.out_qs
        for q in qs:
            if q.id == qid:
                return True
        return False

    def q_exist(self, q: types.APIQueue):
        return self.in_q_exist(q.id) or self.out_q_exist(q.id)

    def add_q(self, q: types.APIQueue):
        if self.q_exist(q):
            raise BrokenPipeError(f"Q already added to proc {self.id}")
        if q.to_p == self.id and not self.in_q_exist(q.id):
            self.in_qs.append(entities.MemQueue(q))
        if q.from_p == self.id and not self.out_q_exist(q.id):
            self.out_qs.append(entities.MemQueue(q))

    def run(self):
        self.execution_status = ProcessorExecutionStatus.RUNNING

    def handle_intra_proc_message(self, msg):
        if msg['control'] == 'run':
            self.run()

    def handle_processor_message(self, msg_json):
        msg = types.UPipeMessage.parse_obj(msg_json)
        if msg.type == types.UPipeMessageType.Q_UPDATE:
            print("Updating queues")
            qs = types.APIProcQueues.parse_obj(msg.body)
            for q in qs.queues:
                queue = qs.queues[q]
                self.add_q(queue)
        if msg.type == types.UPipeMessageType.CONFIG_UPDATE:
            print("Updating config")
            self.config = msg.body
        if msg.type == types.UPipeMessageType.REGISTRATION_INFO:
            print("Updating registration info")
            self.instance_id = msg.body['instance_id']
        if msg.type == types.UPipeMessageType.REQUEST_TERMINATION:
            print("Termination request")
            self.request_termination = True

    def handle_pipelines_message(self, msg_json):
        raise NotImplementedError("Only pipeline object can handle pipeline messages")

    def on_ws_message(self, msg: UPipeMessage):
        if msg.scope == UPipeEntityType.PROCESSOR:
            self.handle_processor_message(msg)
        if msg.scope == UPipeEntityType.PIPELINE:
            self.handle_pipelines_message(msg)

    def get_current_message_data(self):
        if self.proc:
            return 1
        return 1

    def get_next_q_to_emit(self):
        if len(self.out_qs) == 0:
            return False
        q = self.out_qs[0]
        return q

    async def enqueue(self, q, frame):
        if q.host:
            added = await self.node_client.put_q(q, frame)
        else:
            added = await q.put(frame)
        if not added:
            return False
        self.enqueue_counter +=1
        return True

    async def emit(self, data, d_type: entities.DType = None):
        if isinstance(data, entities.DataFrame):
            frame = data
        else:
            frame = entities.DataFrame(data)
        if self.current_pipe_execution_id:
            frame.set_pipe_exe_id(self.current_pipe_execution_id)
        q = self.get_next_q_to_emit()
        if not q and self.sink_q:
            return await self.enqueue(self.sink_q, frame)
        if not q:
            print(f"Warning:Processor {self.name} emit dropped: No destination")
            return False
        success = True
        for q in self.out_qs:
            success = success and await self.enqueue(q, frame)
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
        (data, messages) = await self.node_client.notify_termination(self.processor_def)
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
    def processor_def(self):
        return types.APIProcessor(name=self.name,
                                  id=self.id,
                                  entry=self.entry,
                                  function=self.function,
                                  interpreter=self.interpreter,
                                  type=self.type,
                                  settings=self.settings,
                                  config=self.config)
