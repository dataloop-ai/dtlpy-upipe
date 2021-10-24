import _thread
import asyncio
import json
import pickle
import platform
from threading import Thread
from typing import Dict

import aiohttp
import websocket
import websockets
import websockets.exceptions
import time
import httpx
from aiohttp import FormData, ClientSession

from mock.sdk import API_Proc, API_Response, API_Node, QStatus, API_Proc_Message, ProcMessageType, NODE_PROC_NAME

counter = 0

host = 'localhost:852'
# ************aiohttp crap **********************
# https://github.com/aio-libs/aiohttp/issues/4324
if platform.system() == 'Windows':
    from functools import wraps

    # noinspection PyProtectedMember
    from asyncio.proactor_events import _ProactorBasePipeTransport


    def silence_event_loop_closed(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except RuntimeError as e:
                if str(e) != 'Event loop is closed':
                    raise

        return wrapper


    # Silence the exception here.
    _ProactorBasePipeTransport.__del__ = silence_event_loop_closed(_ProactorBasePipeTransport.__del__)


# ************aiohttp crap end **********************

def retry(times: int, exceptions=()):
    """
    Retry Decorator
    Retries the wrapped function/method `times` times if the exceptions listed
    in ``exceptions`` are thrown
    :param exceptions: Tuple of Exceptions
    :param times: The number of times to repeat the wrapped function/method
    :type times: Int
    :param Exceptions: Lists of exceptions that trigger a retry attempt
    """

    def decorator(func):
        async def newfn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    res = await func(*args, **kwargs)
                    content = API_Response(**await res.json())
                    if content.success:
                        return (content.data,content.messages)
                    else:
                        raise AssertionError(f"Error on {func} : {content.messages}")
                except exceptions:
                    print(
                        'Exception thrown when attempting to run %s, attempt '
                        '%d of %d' % (func, attempt, times)
                    )
                attempt += 1
                await asyncio.sleep(1)
            raise TimeoutError(f"Error on server access {func}")

        return newfn

    return decorator


class NodeClient:
    socket: websockets.WebSocketClientProtocol
    sessions: Dict[str, ClientSession] = {}
    _server_session: ClientSession = None

    def __init__(self, proc_name, message_handler=None):
        self.register_timeout = 5
        self.proc_name = proc_name
        self.message_handler = message_handler
        self.socket: websocket.WebSocketApp = None
        self.connected = False
        self.keep_alive = False
        self.terminate = False  # just before we go ...

    # noinspection PyBroadException
    async def cleanup(self):
        start_time = time.time()
        while True:
            try:
                for proc_name in self.sessions:
                    s = self.sessions[proc_name]
                    if s:
                        await s.close()
                    self.sessions = []
                if self._server_session:
                    await self._server_session.close()
                    self._server_session = None
                if self.socket:
                    await self.socket.drain()
                    await self.socket.close_connection()
                    self.socket = None
                elapsed = time.time() - start_time
                if elapsed > 3:
                    break
            except:
                break

    @retry(times=3)
    async def ping(self):
        ping_url = f"http://{host}/ping"
        return await self.server_session.get(ping_url)

    @retry(times=3)
    async def register_proc(self, proc: API_Proc):
        register_url = f"http://{host}/register_proc"
        return await self.server_session.post(register_url, json=proc.dict())

    @retry(times=3)
    async def register_node(self, node: API_Node):
        register_url = f"http://{host}/register_node"
        return await self.server_session.post(register_url, json=node.dict())

    @retry(times=3)
    async def serve(self):
        serve_url = f"http://{host}/serve"
        return await self.server_session.get(serve_url)

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

    def send_message(self, msg: API_Proc_Message):
        if not self.socket:
            return
        self.socket.send(msg.json())

    def handle_message(self, message):
        global counter
        msg = json.loads(message)
        try:
            api_msg = API_Proc_Message.parse_obj(msg)
            if self.message_handler:
                self.message_handler(api_msg)
        except:
            return


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
    def server_session(self):
        if not self._server_session:
            self._server_session = aiohttp.ClientSession()
        return self._server_session

    @property
    def ws_url(self):
        return f"ws://{host}/ws/connect/{self.proc_name}"

    def on_message(self, ws, message):
        self.handle_message(message)

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        print("### closed ###")

    def on_open(self, ws):
        print(f"{self.proc_name} connected")
        self.socket = ws
        self.connected = True

    def report_q_status(self, proc: API_Proc, q_status: QStatus):
        msg = API_Proc_Message(dest=NODE_PROC_NAME, type=ProcMessageType.Q_STATUS, sender=proc, body=q_status.dict())
        self.send_message(msg)

    def connect_socket(self):
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(self.ws_url,
                                    on_open=self.on_open,
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close)
        ws.run_forever()

    async def connect(self, timeout: int = 10):
        if self.socket:
            return True
        thread = Thread(target=self.connect_socket)
        thread.start()
        sleep_time = .5
        while not self.connected:
            await asyncio.sleep(sleep_time)
            if self.connected:
                return True
        # start_time = time.time()
        # sleep_time = .5
        # self.connected = True
        # while True:
        #     if self.connected:
        #         return True
        #     elapsed = start_time - time.time()
        #     if elapsed > timeout:
        #         raise TimeoutError(f"connect timeout {elapsed} sec")
        #     await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    pass
