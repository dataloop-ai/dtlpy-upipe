import subprocess
import subprocess
import sys

from .client import *
from .manager import *

default_port = 2992
server_process = None

def start_node():
    interpreter_path = sys.executable
    root_path = manager.ComputeNode.root_path()
    node_exe_path = os.path.join(root_path, "node_main.py")
    return subprocess.Popen([interpreter_path, node_exe_path])


node_process = None


def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor


spinner = spinning_cursor()


def start_server():
    global server_process
    if server_process:
        return
    pid_log.start_session(os.getpid())
    server_process = manager.ComputeNode.launch_server()
    pid_log.log_pid(server_process.pid, "node server")
    nuke_time = 10
    start_time = time.time()
    while not manager.ComputeNode.is_server_available():
        # elapsed = time.time() - start_time
        # if elapsed > nuke_time:
        #     print("Restarting node")
        #     ComputeNode.kill_em_all()
        #     ComputeNode.launch_server()
        #     start_time = time.time()
        print(f"Waiting for node")
        time.sleep(3)
    print(f"Server ping ok")


async def wait_for_node_ready():
    global node_process
    if node_process:
        return
    _node_process = None
    if manager.ComputeNode.nodes_process_count() > 1:
        manager.ComputeNode.kill_em_all()
    if manager.ComputeNode.is_node_ready():
        print("Connecting to existing node")
        _node_process = manager.ComputeNode.get_node_process()
        return
    else:
        print("Starting node")
        manager.ComputeNode.kill_em_all()
        _node_process = start_node()
    nuke_time = 10
    start_time = time.time()
    while not manager.ComputeNode.is_node_ready():
        elapsed = time.time() - start_time
        if elapsed > nuke_time:
            print("Restarting node")
            manager.ComputeNode.kill_em_all()
            _node_process = start_node()
            start_time = time.time()
        print(f"Waiting for node")
        time.sleep(3)
    node_process = _node_process
    return _node_process
