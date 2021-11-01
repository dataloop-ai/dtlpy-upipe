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
        self.node_client = node.NodeClient(self.name)
        self.execution_status = ProcessorExecutionStatus.RUNNING
        self.consumer_next_q_index = 0
        self.interpreter = sys.executable
        self.request_termination = False  # called from manager to notify its over
        # self.smd = shared_memory_dict.SharedMemoryDict(name=name, size=1025)
        atexit.register(self.cleanup)
        # processor_memory_name = f"processor_control:{self.name}"
        # try:
        #     self.mem = shared_memory.SharedMemory(name=processor_memory_name, create=True, size=self.SHARED_MEM_SIZE)
        #     self.mem.buf[:] = bytearray(self.SHARED_MEM_SIZE)
        # except FileExistsError:
        #     self.mem = shared_memory.SharedMemory(name=processor_memory_name, size=self.SHARED_MEM_SIZE)

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
        for m in messages:
            message = types.APIPipeMessage.parse_obj(m)
            self.handle_message(message)
        self.registered = True
        return self.registered

    def start(self):
        pass

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
            raise BrokenPipeError(f"Q already added to proc {self.name}")
        if q.to_p == self.name and not self.in_q_exist(q.id):
            self.in_qs.append(entities.MemQueue(q))
        if q.from_p == self.name and not self.out_q_exist(q.id):
            self.out_qs.append(entities.MemQueue(q))

    def run(self):
        self.execution_status = ProcessorExecutionStatus.RUNNING

    def handle_intra_proc_message(self, msg):
        if msg['control'] == 'run':
            self.run()

    def handle_message(self, msg: types.APIPipeMessage):
        if msg.type == types.PipeMessageType.Q_UPDATE:
            print("Updating queues")
            qs = types.APIProcQueues.parse_obj(msg.body)
            for q in qs.queues:
                queue = qs.queues[q]
                self.add_q(queue)
        if msg.type == types.PipeMessageType.CONFIG_UPDATE:
            print("Updating config")
            self.config = msg.body
        if msg.type == types.PipeMessageType.REGISTRATION_INFO:
            print("Updating registration info")
            self.instance_id = msg.body['instance_id']
        if msg.type == types.PipeMessageType.PROC_TERMINATE:
            print("Termination request")
            self.request_termination = True

    def on_ws_message(self, msg):
        msg = types.APIPipeMessage(msg)
        self.handle_message(msg)

    def get_current_message_data(self):
        if self.proc:
            return 1
        return 1

    def get_next_q_to_emit(self):
        if len(self.out_qs) == 0:
            raise MemoryError
        q = self.out_qs[0]
        return q

    async def enqueue(self, q, msg):
        if q.host:
            added = await self.node_client.put_q(q, msg)
        else:
            added = await q.put(msg)
        if not added:
            return False
        return True

    async def emit(self, data, d_type: entities.DType = None):
        msg = entities.DataFrame(data, d_type)
        q = self.get_next_q_to_emit()
        success = True
        for q in self.out_qs:
            success = success and await self.enqueue(q, msg)
        return success

    async def emit_sync(self, data, d_type: entities.DType = None):
        msg = entities.DataFrame(data, d_type)
        while not await self.out_qs[0].space_available(msg):
            await asyncio.sleep(.1)
        return await self.emit(data, d_type)

    async def get(self):
        sys.stdout.flush()
        if self.request_termination:
            raise GeneratorExit("Process terminated by node manager")
        for i in range(len(self.in_qs)):
            next_index = (self.consumer_next_q_index + i) % len(self.in_qs)
            q: entities.MemQueue = self.in_qs[next_index]
            frame = await q.get()
            if frame:
                self.consumer_next_q_index += 1
                return frame.data
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

    @property
    def config_hash(self):
        if len(self.config):
            return ""
        config_md5 = hashlib.md5(json.dumps(self.config, sort_keys=True).encode('utf-8')).hexdigest()
        return config_md5

    @property
    def id(self):
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
                                  type=types.PipeEntityType.PROCESSOR,
                                  settings=self.settings,
                                  config=self.config)
