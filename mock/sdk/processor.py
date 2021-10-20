import asyncio
import time
from enum import IntEnum
from typing import List, Dict

import websocket

from .dataframe import DType, DataFrame
from .mem_queue import Queue
import sys
import subprocess
from .node_config import node_config
import os
from .node import NodeClient


class ProcessorExecutionStatus(IntEnum):
    READY = 1
    PAUSED = 2
    RUNNING = 3


class Processor:
    ...
    next_serial = 0
    in_qs: List[Queue]
    out_qs: List[Queue]

    async def waiter(self, event):
        print('waiting for it ...')
        await event.wait()
        self.on_frame_callback(self.get_current_message_data())

    def __init__(self, name=None, path=None, host=None):  # name is unique per pipe
        if not name:
            name = sys.argv[0]
            print(f"Warning:Nameless processor started:{name}")
        self.host = host
        self.in_qs = []
        self.out_qs = []
        self.serial = None
        self.registered = False
        self.controller = False
        self.proc = None
        self.path = path
        self.on_frame_callback = None
        self.name = name
        self.length = 10
        self.children = list()
        self.machine_id = node_config.machine_id
        self.pid = os.getpid()
        self.exe_name = os.path.basename(os.path.abspath(sys.modules['__main__'].__file__))
        self.proc_id = f"{self.machine_id}:{self.pid}"
        self.node_client = NodeClient(self.name)
        self.execution_status = ProcessorExecutionStatus.RUNNING
        print(f"Processor up: {self.machine_id}  ->{self.exe_name}  (pid {self.pid})")
        self.default_q_size = 1000 * 4096
        # self.smd = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    async def register(self):
        messages = await self.node_client.register(self.on_ws_message)
        if messages:
            self.registered = True
            for m in messages:
                self.handle_message(m)
        return self.registered

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

    async def connect(self):
        if not self.registered:
            await self.register()
        await self.node_client.connect()

    def get_child(self, name):
        proc = next((p for p in self.children if p.name == name), None)
        return proc

    async def send_message(self, to_proc_name, body: Dict):
        msg = {"type": "intra_proc", "dest": to_proc_name, "body": body}
        return await self.node_client.send_message(msg)

    def enum(self):
        self.serial = Processor.next_serial
        Processor.next_serial += 1
        for p in self.children:
            p.enum()

    def allocate_queues(self):
        allocated = []
        for p in self.children:
            q_id = Queue.allocate_id()
            q = Queue(self.name, p.name, q_id, self.default_q_size, p.host)
            allocated.append(q)
            allocated.extend(p.allocate_queues())
        return allocated

    async def monitor(self):
        while True:
            if self.execution_status == ProcessorExecutionStatus.RUNNING:
                await self.process_in_q()
                await asyncio.sleep(.1)
            else:
                await asyncio.sleep(.5)

    def start(self):
        started = []
        if self.path:
            started.append(self)
            py_path = sys.executable
            self.proc = subprocess.Popen([py_path, self.path],
                                         stdout=subprocess.PIPE)
        for p in self.children:
            started.extend(p.start())
        loop = asyncio.get_event_loop()
        loop.create_task(self.monitor())
        return started

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

    def on_frame(self, on_frame):
        # sys.exit("Or, on frame is not supported anymore, use get or get_sync")
        self.on_frame_callback = on_frame

    def get_q(self, q_id, in_q=True):
        qs = self.in_qs
        if not in_q:
            qs = self.out_qs
        for q in qs:
            if q.q_id == q_id:
                return q
        return None

    def add_q(self, q):
        if q["to_p"] == self.name and not self.get_q(q['q_id']):
            self.in_qs.append(Queue(q['from_p'], q['to_p'], q['q_id'], int(q['size']), q['host']))
        if q["from_p"] == self.name and not self.get_q(q['q_id'], False):
            self.out_qs.append(Queue(q['from_p'], q['to_p'], q['q_id'], int(q['size']), q['host']))

    async def process_in_q(self):
        if len(self.in_qs) == 0:
            return
        q: Queue = self.in_qs[0]
        while True:
            frame = await q.get()
            if frame and self.on_frame_callback:
                self.on_frame_callback(frame)
            else:
                break

    def run(self):
        self.execution_status = ProcessorExecutionStatus.RUNNING

    def handle_intra_proc_message(self, msg):
        if msg['type'] == 'q_pending':
            loop = asyncio.get_event_loop()
            loop.create_task(self.process_in_q())

    def handle_intra_proc_message(self, msg):
        if msg['control'] == 'run':
            self.run()

    def handle_message(self, msg):
        if 'type' not in msg:
            raise ValueError
        if msg['type'] == "q_update":
            qs = msg["queues"]
            for q in qs:
                self.add_q(q)
        if msg['type'] == "intra_proc":
            self.handle_intra_proc_message(msg['body'])
        if msg['type'] == "broadcast":
            self.handle_broadcast_message(msg['body'])

    def on_ws_message(self, msg):
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

    def get_next_q_to_process(self):
        if len(self.in_qs) == 0:
            raise MemoryError
        q = self.in_qs[0]
        return q

    async def enqueue(self, q, msg):
        if q.host:
            added = await self.node_client.put_q(q, msg)
        else:
            added = await q.put(msg)
        if not added:
            return False
        return True

    async def emit(self, data, d_type: DType = None):
        msg = DataFrame(data, d_type)
        q = self.get_next_q_to_emit()
        success = True
        for q in self.out_qs:
            success = success and await self.enqueue(q, msg)
        return success

    async def emit_sync(self, data, d_type: DType = None):
        msg = DataFrame(data, d_type)
        while not await self.out_qs[0].space_available(msg):
            await asyncio.sleep(.1)
        return await self.emit(data, d_type)

    async def get(self):
        q: Queue = self.in_qs[0]
        frame = await q.get()
        if frame:
            return frame.data
        return None

    async def get_sync(self, timeout: int = 5):
        q: Queue = self.in_qs[0]
        start_time = time.time()
        sleep_time = 0.01
        while True:
            frame = await q.get()
            if frame:
                return frame.data
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"get_sync timeout {elapsed} sec")
            await asyncio.sleep(sleep_time)
