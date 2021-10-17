import asyncio
import json

import websockets
import time
import httpx

counter = 0

host = 'localhost:852'


class NodeClient:
    socket: websockets.WebSocketClientProtocol

    def __init__(self, proc_name):
        self.register_timeout = 5
        self.proc_name = proc_name
        self.message_handler = None
        self.socket = None
        self.connected = False
        self.keep_alive = False

    def register(self, message_handler):
        messages = self._request_register()
        if messages:
            self.message_handler = message_handler
        return messages

    def register_controller(self, message_handler):
        res = self._request_register(True)
        if res:
            self.message_handler = message_handler
        return res

    def _request_register(self, controller=False):
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

    def serve(self, ):
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

    def register_queue(self, q):
        data = {'from_p': q.from_p, 'to_p': q.to_p, 'id': q.id}
        register_url = f"http://{host}/register_q"
        registered = False
        timer = 0
        while not registered:
            try:
                r = httpx.post(register_url, json=data)
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

    @property
    def ws_url(self):
        return f"ws://{host}/ws/connect/{self.proc_name}"

    async def keep_connection_alive(self):
        while True:
            if not self.connected:
                self.socket = await websockets.connect(self.ws_url)
                self.connected = True
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

    def connect(self):
        if self.keep_alive:
            return True
        asyncio.create_task(self.keep_connection_alive())
        asyncio.create_task(self._process())
        self.keep_alive = True


if __name__ == "__main__":
    pass
