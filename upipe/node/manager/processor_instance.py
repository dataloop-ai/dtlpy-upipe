import time
from enum import IntEnum
from queue import Empty
from threading import Thread

import psutil
from colorama import Fore, Back, Style

from upipe.types import UPipeEntityType


class InstanceType(IntEnum):
    PROCESS = 1
    SUB_PROCESS = 2


class InstanceState(IntEnum):
    LAUNCHED = 1
    READY = 2
    RUNNING = 3
    PAUSED = 4
    DONE = 5


class ProcessorInstance:
    colors = [(Fore.WHITE, Back.BLACK), (Fore.RED, Back.GREEN), (Fore.BLUE, Back.WHITE), (Fore.BLACK, Back.BLUE),
              (Fore.RED, Back.WHITE),
              ]
    next_color_index = 0

    def __init__(self, proc, process, instance_type=InstanceType.SUB_PROCESS, stdout_q=None):
        self.proc = proc
        self.root_process = process
        self.running_process = None
        self.instance_type = instance_type
        self.stdout_q = stdout_q
        self.color_index = ProcessorInstance.next_color_index
        self.state = InstanceState.LAUNCHED
        ProcessorInstance.next_color_index += 1
        if ProcessorInstance.next_color_index >= len(self.colors):
            ProcessorInstance.next_color_index = 0
        thread = Thread(target=self.monitor, daemon=True)
        thread.start()

    def register(self, pid: int):
        self.state = InstanceState.READY
        if self.pid == pid:
            return
        if self.is_child_process(pid):
            return
        raise BrokenPipeError(f"Can not register PID to instance {self.name}")

    def handle_exit(self):
        if self.instance_type == InstanceType.SUB_PROCESS:
            lines = self.root_process.stdout.readlines()
            for line in lines:
                self.stdout_q.write(line)
        self.state = InstanceState.DONE

    def monitor(self):
        while True:
            if self.exit_code is not None:
                self.handle_exit()
                break
            if self.instance_type == InstanceType.SUB_PROCESS:
                if self.root_process.stdout:
                    self.stdout_q.write(self.root_process.stdout.readline())
            time.sleep(1)

    @property
    def color(self):
        return self.colors[self.color_index]

    @property
    def name(self):
        return self.proc.name

    @property
    def proc_id(self):
        return self.proc.id

    @property
    def pid(self) -> int:
        return self.root_process.pid

    @property
    def cpu(self):
        try:
            p = psutil.Process(self.pid)
            return p.cpu_percent()
        except psutil.NoSuchProcess:
            return 0

    @property
    def memory(self):
        try:
            p = psutil.Process(self.pid)
            return p.memory_percent()
        except psutil.NoSuchProcess:
            return 0

    @property
    def exit_code(self):
        if self.instance_type == InstanceType.SUB_PROCESS:
            return self.root_process.poll()
        if self.instance_type == InstanceType.PROCESS:
            return self.root_process.exitcode
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
        line = f"{self.name}({self.pid})" + self.color[0] + self.color[1] + ">>>" + Style.RESET_ALL + f"{line}"
        return line

    @property
    def is_done(self):
        return self.state == InstanceState.DONE

    @property
    def is_launched(self):
        return self.state == InstanceState.LAUNCHED

    @property
    def api_def(self):
        from ...types import APIProcessorInstance
        return APIProcessorInstance(**self.proc, pid=self.pid, id=self.pid, type=UPipeEntityType.PROCESSOR_INSTANCE)

    def is_child_process(self, pid: int):
        child_processes = psutil.Process(self.pid).children(recursive=True)
        for p in child_processes:
            if p.pid == pid:
                return True
        return False
