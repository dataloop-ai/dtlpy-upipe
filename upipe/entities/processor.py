import hashlib
import json
import os
import sys
from enum import IntEnum

from colorama import init

from .. import node, types

init(autoreset=True)


class ProcessorExecutionStatus(IntEnum):
    READY = 1
    PAUSED = 2
    RUNNING = 3


class Processor:
    ...
    next_serial = 0
    SHARED_MEM_SIZE = 64

    def __init__(self,
                 name,
                 entry=None,
                 func=None,
                 settings: types.APIProcSettings = types.APIProcSettings(),
                 config: dict = None):  # name is unique per pipe

        self.instance_id = -1
        self.settings = settings
        self.input_buffer_size = settings.input_buffer_size
        self.host = settings.host
        self.autoscale = settings.autoscale
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
        self.exe_name = os.path.basename(os.path.abspath(sys.modules['__main__'].__file__))
        self.interpreter = sys.executable
        self.request_termination = False  # called from manager to notify its over
        self.type = types.UPipeEntityType.PROCESSOR
        self.node_client = node.NodeClient(self.processor_def, self.id)
        self.current_pipe_execution_id = None

    def add(self, processor):
        if self.get_child(processor.name):
            return
        print("Adding {}".format(processor.name))
        self.children.append(processor)

        return processor

    def get_child(self, name):
        proc = next((p for p in self.children if p.name == name), None)
        return proc

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
