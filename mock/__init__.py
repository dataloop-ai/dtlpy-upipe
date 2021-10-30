import asyncio
import os
import subprocess
import sys
import time

node_process = None


def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor


spinner = spinning_cursor()

def start_server():
    from .sdk.node.manager.node_main import ComputeNode
    ComputeNode.launch_server()
    nuke_time = 10
    start_time = time.time()
    while not ComputeNode.is_server_available():
        # elapsed = time.time() - start_time
        # if elapsed > nuke_time:
        #     print("Restarting node")
        #     ComputeNode.kill_em_all()
        #     ComputeNode.launch_server()
        #     start_time = time.time()
        print(f"Waiting for node")
        time.sleep(3)



def start_node():
    from .sdk.node.manager.node_main import ComputeNode
    interpreter_path = sys.executable
    root_path = ComputeNode.root_path()
    node_exe_path = os.path.join(root_path, "node_main.py")
    return subprocess.Popen([interpreter_path, node_exe_path])


async def wait_for_node_ready():
    global node_process
    if node_process:
        return
    _node_process = None
    from .sdk.node.manager.node_main import ComputeNode
    if ComputeNode.nodes_process_count() > 1:
        ComputeNode.kill_em_all()
    if ComputeNode.is_node_ready():
        print("Connecting to existing node")
        _node_process = ComputeNode.get_node_process()
        return
    else:
        print("Starting node")
        ComputeNode.kill_em_all()
        _node_process = start_node()
    nuke_time = 10
    start_time = time.time()
    while not ComputeNode.is_node_ready():
        elapsed = time.time() - start_time
        if elapsed > nuke_time:
            print("Restarting node")
            ComputeNode.kill_em_all()
            _node_process = start_node()
            start_time = time.time()
        print(f"Waiting for node")
        time.sleep(3)
    node_process = _node_process
    return _node_process
