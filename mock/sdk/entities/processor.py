import asyncio
import time
from enum import IntEnum
from multiprocessing import shared_memory
from threading import Thread
from typing import List, Dict

from aiohttp import ClientConnectorError
from colorama import init, Fore

import psutil

from mock.sdk import API_Proc, ProcUtilizationEntry, QStatus, API_Proc_Message, ProcMessageType
from .dataframe import DType, DataFrame
from .mem_queue import Queue
import sys
import subprocess

import os
import mock.sdk.node.client as client
import atexit

from ..utils import processor_shared_memory_name

init(autoreset=True)


class ProcessorExecutionStatus(IntEnum):
    READY = 1
    PAUSED = 2
    RUNNING = 3


class Processor:
    ...
    next_serial = 0
    in_qs: List[Queue]
    out_qs: List[Queue]
    SHARED_MEM_SIZE = 64

    def __init__(self, name=None, entry=None, func=None, host=None, autoscale=1,
                 input_buffer_size=1000 * 4096):  # name is unique per pipe
        if not name:
            name = sys.argv[0]
            print(f"Warning:Nameless processor started:{name}")
        self.input_buffer_size = input_buffer_size
        self.host = host
        self.in_qs = []
        self.out_qs = []
        self.serial = None
        self.registered = False
        self.connected = False
        self.controller = False
        self.proc = None
        self.entry = entry
        self.function = None
        self.autoscale = autoscale
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
        self.node_client = client.NodeClient(self.name)
        self.execution_status = ProcessorExecutionStatus.RUNNING
        self.consumer_next_q_index = 0
        self.interpreter = sys.executable
        self.request_termination = False  # called from manager to notify its over
        # self.smd = shared_memory_dict.SharedMemoryDict(name=name, size=1025)
        atexit.register(self.cleanup)
        processor_memory_name = processor_shared_memory_name(self.api_def)
        try:
            self.mem = shared_memory.SharedMemory(name=processor_memory_name, create=True, size=self.SHARED_MEM_SIZE)
            self.mem.buf[:] = bytearray(self.SHARED_MEM_SIZE)
        except FileExistsError:
            self.mem = shared_memory.SharedMemory(name=processor_memory_name, size=self.SHARED_MEM_SIZE)

    def cleanup(self):
        print(Fore.BLUE + f"Processor cleanup : {self.name}")
        for task in asyncio.Task.all_tasks():
            task.cancel()
        loop = asyncio.get_event_loop()
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
        if self.registered:
            return
        printed = False
        while True:
            try:
                (data, messages) = await self.node_client.register_proc(self.api_def)
                break
            except ClientConnectorError:
                if not printed:
                    print("Waiting for node controller ...")
                    printed = True
                await asyncio.sleep(5)
        for m in messages:
            self.handle_message(m)
        self.registered = True
        return self.registered

    def start(self):
        pass

    async def connect(self):
        if not self.registered:
            await self.register()
        if not self.connected:
            self.connected = await self.node_client.connect()
        thread = Thread(target=self.monitor)
        thread.start()

    def get_child(self, name):
        proc = next((p for p in self.children if p.name == name), None)
        return proc

    def enum(self):
        self.serial = Processor.next_serial
        Processor.next_serial += 1
        for p in self.children:
            p.enum()

    def allocate_queues(self):
        allocated = []
        for p in self.children:
            q_id = Queue.allocate_id()
            q = Queue(self.name, p.name, q_id, self.input_buffer_size, p.host)
            allocated.append(q)
            allocated.extend(p.allocate_queues())
        return allocated

    def report_q_status(self):
        current_time = time.time() * 1000  # ms
        pending = 0
        for q in self.in_qs:
            pending += q.log.pending_stats
        status = QStatus(q_id=q.q_id, pending=pending, time=current_time)
        self.node_client.report_q_status(self.api_def, status)

    def monitor(self):
        while True:
            time.sleep(1)
            if not self.connected:
                continue
            self.report_q_status()

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
        sys.exit("Or, on frame is not supported anymore, use get or get_sync")
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

    def run(self):
        self.execution_status = ProcessorExecutionStatus.RUNNING

    def handle_intra_proc_message(self, msg):
        if msg['control'] == 'run':
            self.run()

    def handle_message(self, msg: API_Proc_Message):
        if msg.type == ProcMessageType.Q_UPDATE:
            print("Q update request")
            qs = msg.body["queues"]
            for q in qs:
                self.add_q(q)
        if msg.type == ProcMessageType.PROC_TERMINATE:
            print("Termination request")
            self.request_termination = True

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
        if self.request_termination:
            raise GeneratorExit("Process terminated by node manager")
        for i in range(len(self.in_qs)):
            next_index = (self.consumer_next_q_index + i) % len(self.in_qs)
            q: Queue = self.in_qs[next_index]
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
    def executable(self):
        return sys.argv[0]

    @property
    def api_def(self):
        return API_Proc(name=self.name, entry=self.entry, function=self.function, interpreter=self.interpreter,
                        pid=self.pid, controller=self.controller, autoscale=self.autoscale)
