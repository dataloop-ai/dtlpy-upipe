import asyncio
import json
import pickle
from typing import Dict

import aiohttp
import websockets
import time
import httpx
from aiohttp import FormData, ClientSession

counter = 0

host = 'localhost:852'


class NodeClient:
    socket: websockets.WebSocketClientProtocol
    sessions: Dict[str, ClientSession] = {}

    def __init__(self, proc_name):
        self.register_timeout = 5
        self.proc_name = proc_name
        self.message_handler = None
        self.socket = None
        self.connected = False
        self.keep_alive = False

    async def register(self, message_handler):
        messages = await self._request_register()
        if messages:
            self.message_handler = message_handler
        return messages

    async def register_controller(self, message_handler):
        res = await self._request_register(True)
        if res:
            self.message_handler = message_handler
        return res

    async def _request_register(self, controller=False):
        register_path = 'register'
        if controller:
            register_path = 'register_controller'
        register_url = f"http://{host}/{register_path}/{self.proc_name}"
        print(register_url)
        registered = False
        timer = 0
        while not registered:
            try:
                r = httpx.get(register_url)
                if r.status_code == 200:
                    res = r.json()
                    if res['Success']:
                        return res['messages']
                time.sleep(1)
                timer += 1
                if timer > self.register_timeout:
                    break
            except httpx.TimeoutException:
                print(f"register timeout for {self.proc_name}")
        if not registered:
            raise TimeoutError("Register timeout")
        return False

    async def serve(self, ):
        serve_url = f"http://{host}/serve"
        ready = False
        timer = 0
        while not ready:
            try:
                r = httpx.get(serve_url)
                if r.status_code == 200:
                    res = r.json()
                    if res['Success']:
                        return True
                time.sleep(1)
                timer += 1
                if timer > self.register_timeout:
                    break
            except httpx.TimeoutException:
                print(f"register timeout for {self.proc_name}")
        if not ready:
            raise TimeoutError("Register timeout")
        return False

    async def register_queue(self, q):
        register_url = f"http://{host}/register_q"
        registered = False
        timer = 0
        while not registered:
            try:
                r = httpx.post(register_url, json=q.api_def.dict())
                if r.status_code == 200:
                    return True
                time.sleep(1)
                timer += 1
                if timer > self.register_timeout:
                    break
            except httpx.TimeoutException:
                print(f"register timeout for {self.proc_name}")
        if not registered:
            raise TimeoutError("Register Q timeout")
        return False

    async def send_message(self, msg):
        if not self.socket:
            return
        await self.socket.send(json.dumps(msg))

    def handle_message(self, message):
        global counter
        msg = json.loads(message)
        if self.message_handler:
            self.message_handler(msg)

    async def get_session(self, q):
        if q.host not in self.sessions:
            self.sessions[q.host] = aiohttp.ClientSession()
        return self.sessions[q.host]

    async def put_q(self, q, frame):
        if not q.host:
            raise LookupError("Q doesnt have host set")
        session: aiohttp.ClientSession = await self.get_session(q)
        url = f"http://{q.host}:852/push_q"
        data = FormData()
        bin_frame = pickle.dumps(frame)
        # data.add_field('q', dict(q.api_def.dict()))
        data.add_field('q', q.api_def.json())
        data.add_field('frame_file', bin_frame, content_type="multipart/form-data")
        resp = await session.post(url, data=data)
        if resp.status != 200:
            return False
        res = await resp.json()
        if not res or "Success" not in res:
            return False
        return res["Success"]

    @property
    def ws_url(self):
        return f"ws://{host}/ws/connect/{self.proc_name}"

    async def keep_connection_alive(self):
        while True:
            if not self.connected:
                try:
                    self.socket = await websockets.connect(self.ws_url)
                    self.connected = True
                except asyncio.exceptions.TimeoutError:
                    pass
            await asyncio.sleep(5)

    async def _process(self):
        while True:
            try:
                if not self.socket:
                    await asyncio.sleep(2)
                    continue
                message = await self.socket.recv()
                self.handle_message(message)

            except websockets.exceptions.ConnectionClosed:
                print('ConnectionClosed')
                self.connected = False
                break

    async def connect(self, timeout: int = 10):
        if self.connected:
            return True
        if not self.keep_alive:
            asyncio.create_task(self.keep_connection_alive())
            asyncio.create_task(self._process())
            self.keep_alive = True
        start_time = time.time()
        sleep_time = .5
        while True:
            if self.connected:
                return True
            elapsed = start_time - time.time()
            if elapsed > timeout:
                raise TimeoutError(f"connect timeout {elapsed} sec")
            await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    pass
