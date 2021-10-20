import os
import subprocess
import sys
from multiprocessing import shared_memory
import socket
from .types import *
from .pipe import Pipe
from .processor import Processor

from .dataframe import DataFrame, DType

from .mem_queue import Queue

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


my_path = os.path.dirname(os.path.abspath(__file__))
server_path = os.path.join(my_path, "node", "server", "server.py")
py_path = sys.executable
node_control_mem_name = "node_control_mem"
node_controller = True
node_server = None

try:
    mem = shared_memory.SharedMemory(name=node_control_mem_name, create=True, size=5000)
except FileExistsError:
    mem = shared_memory.SharedMemory(name=node_control_mem_name, size=5000)
    node_controller = False
if node_controller:
    print("starting node server")
    if is_port_in_use(852):
        sys.exit("Server port already in use")
    node_server = subprocess.Popen([py_path, server_path])
