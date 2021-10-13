from .queue import Queue
import sys
import subprocess


class Processor:
    ...

    async def waiter(self, event):
        print('waiting for it ...')
        await event.wait()
        self.on_data_callback(self.get_current_message_data())

    def __init__(self, name, path=None):  # name is unique per pipe
        self.proc = None
        self.path = path
        self.on_data_callback = None
        self.name = name
        self.length = 10
        self.children = list()
        self.inQ = Queue('{}_in'.format(self.name), self.on_message)
        self.outQ = Queue('{}_out'.format(self.name))
        # self.smd = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    def add(self, processor):
        if self.get(processor.name):
            return
        print("Adding {}".format(processor.name))
        self.children.append(processor)
        return processor

    def get(self, name):
        proc = next((p for p in self.children if p.name == name), None)
        return proc

    def start(self):
        started = []
        if self.path:
            started.append(self)
            py_path = sys.executable
            self.proc = subprocess.Popen([py_path, self.path],
                                         stdout=subprocess.PIPE)
        for p in self.children:
            started.extend(p.start())
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

    def on_data(self, on_data):
        self.on_data_callback = on_data

    def on_message(self, msg):
        if self.on_data_callback:
            self.on_data_callback(msg.data)

    def get_current_message_data(self):
        if self.proc:
            return 1
        return 1

    def emit(self, data):
        self.outQ.put(bytearray(data))
