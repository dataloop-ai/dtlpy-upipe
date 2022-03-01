import os
from typing import Callable, Union, List

import psutil
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from ...types import parse_message, UPipeMessage
import copy
import json
import asyncio


def kill_process(pid):
    if pid is None or pid == 0:
        return
    try:
        p = psutil.Process(pid)
        p.terminate()  # or p.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return


def kill_by_path(process_path):
    if not process_path:
        raise ValueError("kill_by_path : path must be a valid process path")
    process = get_process_by_path(process_path)
    if not process:
        raise EnvironmentError("kill_by_path : process want not found")
    print(f"Closing old process : {process_path} ({process.pid})")
    process_pid = process.pid
    return kill_process(process_pid)


def get_process_by_path(process_path):
    processes = get_all_process_by_path(process_path)
    if len(processes):
        return processes[0]
    return None


def get_all_process_by_path(process_path):
    if not process_path:
        raise ValueError("kill_by_path : path must be a valid process path")
    processes = []
    for p in psutil.process_iter():
        try:
            cmdline = p.cmdline()
            if process_path in cmdline:
                processes.append(p)
        except psutil.AccessDenied:
            continue
    return processes


def count_process_by_path(process_path):
    return len(get_all_process_by_path(process_path))


def kill_em_all(process_path, but_me=True):
    if not process_path:
        raise ValueError("kill_by_path : path must be a valid process path")
    killed = 0
    for process in psutil.process_iter():
        try:
            cmdline = process.cmdline()
            if process_path in cmdline:
                if process.pid == os.getpid() and but_me:
                    continue
                kill_process(process.pid)
                killed += 1
        except psutil.AccessDenied:
            continue
    return killed


def kill_port_listener(port: int):
    for process in psutil.process_iter():
        for conns in process.connections(kind='inet'):
            if conns.laddr.port == port:
                kill_process(process.pid)


class WebsocketHandler:
    def __init__(self, name: str, websocket: WebSocket, on_message: Callable):
        self.msg_counter = 0
        self.name = name
        self.socket = websocket
        self.on_message = on_message
        self.message_counter = 0
        self.state_hash = None
        self.connect_requested = False


    def make_hash(self, o):

        """
        Makes a hash from a dictionary, list, tuple or set to any level, that contains
        only other hashable types (including any lists, tuples, sets, and
        dictionaries).
        """

        if isinstance(o, (set, tuple, list)):

            return tuple([self.make_hash(e) for e in o])

        elif not isinstance(o, dict):

            return hash(o)

        new_o = copy.deepcopy(o)
        for k, v in new_o.items():
            new_o[k] = self.make_hash(v)

        return hash(tuple(frozenset(sorted(new_o.items()))))

    async def init(self):
        await self.socket.accept()
        self.connect_requested = True

    async def monitor(self):
        if not self.connect_requested:
            self.init()
        try:
            while True:
                websocket = self.socket
                data = await websocket.receive_text()
                msg = json.loads(data)
                parsed = parse_message(msg)
                self.msg_counter += 1
                try:
                    if self.on_message:
                        self.on_message(parsed)
                except Exception as e:
                    raise ValueError(f"Un supported message:{self.name}")
        except WebSocketDisconnect:
            print(f"connection lost: {self.name}")
            raise WebSocketDisconnect
        except Exception as e:
            raise ValueError(f"Error parsing  message: {self.name}")

    async def send(self, msg: Union[UPipeMessage, List[UPipeMessage]]):
        if not isinstance(msg, list):
            msg = [msg]
        json_messages = [m.dict() for m in msg]
        # hash_ = msg.hash()
        # if hash_ == self.state_hash:
        #     return
        # self.state_hash = hash_
        await self.socket.send_json(json_messages)

    def send_sync(self, msg: UPipeMessage):
        loop = asyncio.get_event_loop()
        loop.create_task(self.send(msg))
