import asyncio
import json
import pickle
import platform
import time
from threading import Thread
from typing import Dict

import aiohttp
import websocket
from aiohttp import FormData, ClientSession

from mock.sdk import API_Proc, API_Response, API_Proc_Message, API_Pipe

counter = 0

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
    """

    def decorator(func):
        async def newfn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                # noinspection PyBroadException
                try:
                    res = await func(*args, **kwargs)
                    res_json = await res.json()
                    content = API_Response(**res_json)
                    if content.success:
                        return content.data, content.messages
                    else:
                        raise AssertionError(f"Error on {func} : {content.messages}")
                except Exception as e:
                    print(
                        'Exception thrown when attempting to run %s, attempt '
                        '%d of %d' % (func.__name__, attempt, times)
                    )
                attempt += 1
                await asyncio.sleep(1)
            raise TimeoutError(f"Error on server access {func}")

        return newfn

    return decorator


# noinspection PyTypeChecker
class NodeClient:
    sessions: Dict[str, ClientSession] = {}
    _server_session: ClientSession = None

    def __init__(self, proc_name, message_handler=None, server_base_url='localhost:852'):
        self.register_timeout = 5
        self.proc_name = proc_name
        self.message_handler = message_handler
        self.socket: websocket.WebSocketApp = None
        self.connected = False
        self.keep_alive = False
        self.terminate = False  # just before we go ...
        self.server_proc = None
        self.server_base_url = server_base_url

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
        ping_url = f"http://{self.server_base_url}/ping"
        return await self.server_session.get(ping_url)

    @retry(times=3)
    async def register_proc(self, proc: API_Proc):
        register_url = f"http://{self.server_base_url}/register_proc"
        return await self.server_session.post(register_url, json=proc.dict())

    @retry(times=10)
    async def register_pipe(self, pipe: API_Pipe):
        register_url = f"http://{self.server_base_url}/register_pipe"
        return await self.server_session.post(register_url, json=pipe.dict())

    def send_message(self, msg: API_Proc_Message):
        if not self.socket:
            return
        self.socket.send(msg.json())

    def handle_message(self, message):
        global counter
        msg = API_Proc_Message.from_json(json.loads(message))
        # noinspection PyBroadException
        try:
            if self.message_handler:
                self.message_handler(msg)
        except Exception as e:
            print(f"Error on message processing :{self.proc_name}:{str(e)}")
            raise ConnectionError(f"Error on socket message: {self.proc_name}")

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
        res: API_Response = API_Response.parse_obj(await resp.json())
        return res.success

    @property
    def server_session(self):
        if not self._server_session:
            self._server_session = aiohttp.ClientSession()
        return self._server_session

    @property
    def ws_url(self):
        return f"ws://{self.server_base_url}/ws/connect/{self.proc_name}"

    def on_message(self, ws, message):
        self.handle_message(message)

    @staticmethod
    def on_error(ws, error):
        print(error)

    @staticmethod
    def on_close(ws, close_status_code, close_msg):
        print("### closed ###")

    def on_open(self, ws):
        print(f"{self.proc_name} connected")
        self.socket = ws
        self.connected = True

    def connect_socket(self):
        websocket.enableTrace(False)
        self.socket = websocket.WebSocketApp(self.ws_url,
                                             on_open=self.on_open,
                                             on_message=self.on_message,
                                             on_error=self.on_error,
                                             on_close=self.on_close)
        self.socket.run_forever()

    def connect(self, timeout: int = 10):
        if self.socket:
            return True
        thread = Thread(target=self.connect_socket, daemon=True)
        thread.start()
        sleep_time = .5
        while not self.connected:
            time.sleep(sleep_time)
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
