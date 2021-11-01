import time
from enum import IntEnum
from queue import Empty
from threading import Thread

import psutil
from colorama import Fore, Back, Style


class InstanceType(IntEnum):
    PROCESS = 1
    SUB_PROCESS = 2


class InstanceState(IntEnum):
    READY = 0
    LAUNCHED = 1
    RUNNING = 2
    DONE = 3


class ProcessorInstance:
    colors = [(Fore.WHITE, Back.BLACK), (Fore.RED, Back.GREEN), (Fore.BLUE, Back.WHITE), (Fore.BLACK, Back.BLUE),
              (Fore.RED, Back.WHITE),
              ]
    next_color_index = 0

    def __init__(self, proc, process, instance_type=InstanceType.SUB_PROCESS, stdout_q=None):
        self.proc = proc
        self.process = process
        self.instance_id = -2
        self.instance_type = instance_type
        self.stdout_q = stdout_q
        self.color_index = ProcessorInstance.next_color_index
        self.state = InstanceState.LAUNCHED
        ProcessorInstance.next_color_index += 1
        if ProcessorInstance.next_color_index >= len(self.colors):
            ProcessorInstance.next_color_index = 0
        thread = Thread(target=self.monitor, daemon=True)
        thread.start()

    def handle_exit(self):
        if self.instance_type == InstanceType.SUB_PROCESS:
            lines = self.process.stdout.readlines()
            for line in lines:
                self.stdout_q.write(line)
        self.state = InstanceState.DONE

    def monitor(self):
        while True:
            if self.exit_code is not None:
                self.handle_exit()
                break
            if self.instance_type == InstanceType.SUB_PROCESS:
                if self.process.stdout:
                    self.stdout_q.write(self.process.stdout.readline())
            time.sleep(1)

    @property
    def color(self):
        return self.colors[self.color_index]

    @property
    def name(self):
        return self.proc.name

    @property
    def cpu(self):
        try:
            p = psutil.Process(self.process.pid)
            return p.cpu_percent()
        except psutil.NoSuchProcess:
            return 0

    @property
    def memory(self):
        try:
            p = psutil.Process(self.process.pid)
            return p.memory_percent()
        except psutil.NoSuchProcess:
            return 0

    @property
    def exit_code(self):
        if self.instance_type == InstanceType.SUB_PROCESS:
            return self.process.poll()
        if self.instance_type == InstanceType.PROCESS:
            return self.process.exitcode
        return None

    def read_stdout_line(self):
        try:
            line = self.stdout_q.get(block=False)
        except Empty:
            line = None
        if self.instance_type == InstanceType.SUB_PROCESS and line:
            line = line.decode().strip()
        if not line or line == '\n' or len(line) == 0:
            return None
        line = f"{self.name}({self.instance_id})" + self.color[0] + self.color[1] + ">>>" + Style.RESET_ALL + f"{line}"
        return line

    @property
    def is_done(self):
        return self.state == InstanceState.DONE

    @property
    def api_def(self):
        from ...types import APIProcessorInstance
        return APIProcessorInstance(**self.proc, instance_id=self.instance_id, pid=self.process.pid)
