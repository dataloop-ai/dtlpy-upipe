import binascii
import os
import time
from enum import IntEnum
from multiprocessing import shared_memory

from pydantic.class_validators import Optional
from pydantic.main import BaseModel

from mock.sdk import API_Queue
from .dataframe import DataFrame

import asyncio

debug = False


def debug_print(*args):
    global debug
    if debug:
        print(*args)


class QLogEntry(BaseModel):
    time: Optional[int]
    frame_counter: int
    alloc_index: int
    exe_index: int
    alloc_counter: int
    exe_counter: int
    pending_counter: int
    free_space: int
    capacity: float
    data_size: int


class QActionLog:
    def __init__(self, entry_limit=60):
        self._enqueue_log = []
        self._dequque_log = []
        self.entry_limit = entry_limit

    def add_to_log(self, entry: QLogEntry, log: list):
        while len(log) > self.entry_limit:
            log.remove(log[0])
        log.append(entry)

    def log_enqueue(self, entry: QLogEntry):
        self.add_to_log(entry, self._enqueue_log)

    def log_dequeue(self, entry: QLogEntry):
        self.add_to_log(entry, self._dequque_log)


def current_milli_time():
    return round((time.time() * 1000) % 60000)


class Q_DIRECTION(IntEnum):
    WRAP = 1
    NORMAL = 1


class LOCK_STATUS(IntEnum):
    OPEN = 1
    LOCKED = 2


class FRAME_STATUS(IntEnum):
    AVAILABLE = 0
    CREATED = 1
    EXECUTING = 2
    RETIRED = 3


class FrameParser:
    def __init__(self, buffer, exe_index):
        self.exe_index = exe_index
        self.frame_status_pointer = exe_index + Queue.FRAME_STATUS_OFFSET
        self.frame_status = buffer[self.frame_status_pointer]
        self.frame_d_type = buffer[exe_index + Queue.FRAME_TYPE_OFFSET]
        self.frame_size_pointer = exe_index + Queue.FRAME_SIZE_OFFSET
        self.frame_size = int.from_bytes(buffer[self.frame_size_pointer:self.frame_size_pointer + 4], "little")
        self.frame_data_pointer = exe_index + Queue.FRAME_HEADER_SIZE
        self.frame_data_size = self.frame_size - Queue.FRAME_HEADER_SIZE
        self.frame_data = bytearray(self.frame_data_size)
        self.frame_data[:] = buffer[self.frame_data_pointer:self.frame_data_pointer + self.frame_data_size]

    def print(self):
        print(f"exe index:{self.exe_index}")
        print(f"frame_status_pointer:{self.frame_status_pointer}")
        print(f"frame_status:{self.frame_status}")
        print(f"frame_d_type:{self.frame_d_type}")
        print(f"frame_size_pointer:{self.frame_size_pointer}")
        print(f"frame_size:{self.frame_size}")
        print(f"frame_data_pointer:{self.frame_data_pointer}")
        print(f"frame_data_size:{self.frame_data_size}")
        print(f"frame_data:{self.frame_data}")


class Queue:
    next_serial = 0
    # frame header space
    FRAME_HEADER_SIZE = 32  # added to every frame
    FRAME_STATUS_OFFSET = 0  # from frame start, size 1
    FRAME_TYPE_OFFSET = 1  # from frame start, size 1
    FRAME_SIZE_OFFSET = 2  # from frame start, size 4
    FRAME_WATERMARK_OFFSET = 6  # from frame start, size 8
    FRAME_CRC32_OFFSET = 14  # from frame start, size 4
    FRAME_NUM_OFFSET = 18  # from frame start, size 4
    # end of frame header space
    # Q header space
    Q_CONTROL_SIZE = 64
    DATA_START_POINT = Q_CONTROL_SIZE
    R_LOCK_POINTER = 6  # size = 4
    W_LOCK_POINTER = 10  # size = 4
    STATUS_POINTER = 14  # size = 1
    DIRECTION_POINTER = 15  # size = 1
    ALLOC_POINTER = 16  # size = 4
    EXE_POINTER = 20  # size = 4
    ALLOC_COUNTER_POINTER = 24  # size = 4
    EXE_COUNTER_POINTER = 28  # size = 4
    # end of Q header
    LOCK_TIMEOUT = 0.5
    LOCK_CHECK_INTERVAL = 0.05
    MAX_CAPACITY = 0.90
    WATER_MARK = bytearray()
    WATER_MARK.extend(map(ord, "d@tal0op"))

    @staticmethod
    def allocate_id():
        q_id = Queue.next_serial
        Queue.next_serial += 1
        return q_id

    def __init__(self, from_p: str, to_p: str, q_id: str, size, host=None):
        self.log: QActionLog = QActionLog()
        min_q_size = self.Q_CONTROL_SIZE + self.FRAME_HEADER_SIZE + 1  # send at least 1 byte ...
        if size < min_q_size:
            raise MemoryError(f"Queue size must be at least {min_q_size}")
        self.frame_counter = 0
        self.q_id = q_id
        self.from_p = from_p
        self.to_p = to_p
        self.length = 10
        self.name = f"{from_p} -> {to_p} ({self.q_id})"
        self.memory_name = f"Q_{q_id}"
        self.size = size
        self.nextMessageAddress = 0
        self.currentAddress = 0
        self.host = host
        try:
            self.mem = shared_memory.SharedMemory(name=self.memory_name, create=True, size=self.size)
            self.mem.buf[:] = bytearray(self.size)
            self.status = LOCK_STATUS.OPEN
            self.direction = Q_DIRECTION.NORMAL
            self.alloc_index = self.DATA_START_POINT
            self.exe_index = self.DATA_START_POINT

        except FileExistsError:
            self.mem = shared_memory.SharedMemory(name=self.memory_name, size=self.size)

    def log_enqueque(self, entry: QLogEntry):
        current_time = time.time() * 1000  # ms
        entry.time = current_time
        self.log.log_enqueue(entry)

    def log_dequeue(self, entry: QLogEntry):
        current_time = time.time() * 1000  # ms
        entry.time = current_time
        self.log.log_dequeue(entry)

    async def get(self):
        try:
            if self.pending_counter == 0:
                return None
            await self.acquire_read_lock()
            capacity = (self.size - self.Q_CONTROL_SIZE - self.free_space) / self.size
            frame_header = bytearray(self.FRAME_HEADER_SIZE)
            start_exe_index = self.exe_index
            # get the frame header
            if self.exe_index + self.FRAME_HEADER_SIZE < self.size:
                frame_header[:] = self.mem.buf[self.exe_index:self.exe_index + self.FRAME_HEADER_SIZE]
            else:
                header_space_left = self.size - self.exe_index
                part1 = self.mem.buf[self.exe_index:]
                part2 = self.mem.buf[
                        self.DATA_START_POINT:self.DATA_START_POINT + self.FRAME_HEADER_SIZE - header_space_left]
                frame_header[:] = part1.tobytes() + part2.tobytes()
            # validate frame
            frame_status = frame_header[self.FRAME_STATUS_OFFSET]
            watermark = frame_header[self.FRAME_WATERMARK_OFFSET:self.FRAME_WATERMARK_OFFSET + 8]
            expected_crc32 = frame_header[self.FRAME_CRC32_OFFSET:self.FRAME_CRC32_OFFSET + 4]
            if frame_status != FRAME_STATUS.CREATED:
                return None
            if watermark != self.WATER_MARK:
                raise BrokenPipeError(
                    f"{current_milli_time()} - Missing watermark on index:{watermark} @ {self.exe_index}")

            frame_d_type = frame_header[self.FRAME_TYPE_OFFSET]
            frame_size = int.from_bytes(frame_header[self.FRAME_SIZE_OFFSET:self.FRAME_SIZE_OFFSET + 4], "little")
            frame_data_size = frame_size - self.FRAME_HEADER_SIZE
            frame_counter = int.from_bytes(frame_header[self.FRAME_NUM_OFFSET:self.FRAME_NUM_OFFSET + 4], "little")
            # log
            self.log_enqueque(
                QLogEntry(frame_counter=frame_counter, alloc_index=self.alloc_index, exe_index=self.exe_index,
                          alloc_counter=self.alloc_counter, exe_counter=self.exe_counter,
                          pending_counter=self.pending_counter, free_space=self.free_space, capacity=capacity,
                          data_size=frame_data_size))
            debug_print(
                f"Get {current_milli_time()}- Frame size:{frame_size}, free space:{self.free_space}, alloc_index:{self.alloc_index},exe_index:{self.exe_index}")
            # get the frame data
            if self.exe_index + self.FRAME_HEADER_SIZE >= self.size:
                frame_data_pointer = self.DATA_START_POINT + (self.exe_index + self.FRAME_HEADER_SIZE) % self.size
            else:
                frame_data_pointer = self.exe_index + self.FRAME_HEADER_SIZE
            frame_data = bytearray(frame_data_size)
            if frame_data_pointer + frame_data_size < self.size:
                frame_data[:] = self.mem.buf[frame_data_pointer:frame_data_pointer + frame_data_size]
            else:
                data_space_left = self.size - frame_data_pointer
                part1 = self.mem.buf[frame_data_pointer:]
                part2 = self.mem.buf[self.DATA_START_POINT:self.DATA_START_POINT + frame_data_size - data_space_left]
                frame_data[:] = part1.tobytes() + part2.tobytes()
            # clear executed frame
            if self.exe_index + frame_size < self.size:
                self.mem.buf[self.exe_index:self.exe_index + frame_size] = bytearray(frame_size)
            else:
                frame_space_left = self.size - self.exe_index
                self.mem.buf[self.exe_index:] = bytearray(frame_space_left)
                self.mem.buf[self.DATA_START_POINT:self.DATA_START_POINT + frame_size - frame_space_left] = bytearray(
                    frame_size - frame_space_left)
            # update execution index
            if self.exe_index + frame_size < self.size:
                self.exe_index = self.exe_index + frame_size
            else:
                self.exe_index = self.DATA_START_POINT + (self.exe_index + frame_size) % self.size
            # validate data
            actual_crc32 = binascii.crc32(frame_data).to_bytes(4, "little")
            if expected_crc32 != actual_crc32:
                print(f"CRC Check: Expected:{expected_crc32},Actual:{actual_crc32}")
                raise BrokenPipeError(f"Frame CRC32 error at index:{start_exe_index}, exe count:{self.exe_counter} ")
            # done
            frame = DataFrame.from_byte_arr(frame_data, frame_d_type)
            self.exe_counter += 1
            return frame
        finally:
            await self.release_read_lock()

    async def space_available(self, msg: DataFrame):
        frame_size = msg.size + self.FRAME_HEADER_SIZE
        if frame_size > self.free_space:
            return False
        return True

    async def put(self, msg: DataFrame):
        capacity = (self.size - self.Q_CONTROL_SIZE - self.free_space) / self.size
        if capacity > self.MAX_CAPACITY:
            return False
        frame_size = msg.size + self.FRAME_HEADER_SIZE
        if frame_size > self.free_space:
            return False
        if self.alloc_index == 2765604:
            pass
        debug_print(
            f"Put {current_milli_time()} - Frame size:{frame_size}, free space:{self.free_space}, alloc_index:{self.alloc_index},exe_index:{self.exe_index}")
        try:
            await self.acquire_write_lock()
            body = msg.byte_arr_data
            header = bytearray(self.FRAME_HEADER_SIZE)
            header[self.FRAME_STATUS_OFFSET] = FRAME_STATUS.CREATED
            header[self.FRAME_TYPE_OFFSET] = msg.d_type
            header[self.FRAME_SIZE_OFFSET:self.FRAME_SIZE_OFFSET + 4] = frame_size.to_bytes(4, "little")
            header[self.FRAME_WATERMARK_OFFSET:self.FRAME_WATERMARK_OFFSET + 8] = self.WATER_MARK
            header[self.FRAME_CRC32_OFFSET:self.FRAME_CRC32_OFFSET + 4] = binascii.crc32(body).to_bytes(4, "little")
            header[self.FRAME_NUM_OFFSET:self.FRAME_NUM_OFFSET + 4] = self.frame_counter.to_bytes(4, "little")
            self.log_enqueque(
                QLogEntry(frame_counter=self.frame_counter, alloc_index=self.alloc_index, exe_index=self.exe_index,
                          alloc_counter=self.alloc_counter, exe_counter=self.exe_counter,
                          pending_counter=self.pending_counter, free_space=self.free_space, capacity=capacity,
                          data_size=len(body)))
            self.frame_counter += 1
            frame = header + body
            end_of_buffer_space = self.size - self.alloc_index
            frame_address = self.alloc_index
            if frame_size >= end_of_buffer_space:  # split the message, end of buffer reached
                debug_print("Q wrap")
                self.mem.buf[frame_address:frame_address + end_of_buffer_space] = frame[0:end_of_buffer_space]
                size_left = frame_size - end_of_buffer_space
                self.mem.buf[self.DATA_START_POINT:self.DATA_START_POINT + size_left] = frame[end_of_buffer_space:]
                self.alloc_index = self.DATA_START_POINT + size_left
                self.direction = Q_DIRECTION.NORMAL
            else:
                self.mem.buf[frame_address:frame_address + frame_size] = frame
                self.alloc_index = self.alloc_index + frame_size
                self.direction = Q_DIRECTION.WRAP
            self.alloc_counter += 1
            return True
        finally:
            await self.release_write_lock()

    def print(self):
        parser = FrameParser(self.mem.buf, self.exe_index)
        parser.print()

    def handle_incoming_message(self):
        msg = DataFrame.from_buffer(self.mem, self.nextMessageAddress)
        if self.on_message:
            self.on_message(msg)

    def get_message(self):
        pass

    def get_frame_status(self, frame_start):
        address = frame_start + self.FRAME_STATUS_OFFSET
        return int.from_bytes(self.mem.buf[address:address + 1], "little")

    def set_frame_status(self, frame_start, status):
        address = frame_start + self.FRAME_STATUS_OFFSET
        self.mem.buf[address:address + 1] = status.to_bytes(1, "little")

    def get_frame_size(self, frame_start):
        address = frame_start + self.FRAME_SIZE_OFFSET
        return int.from_bytes(self.mem.buf[address:address + 4], "little")

    def set_frame_size(self, frame_start, size):
        address = frame_start + self.FRAME_SIZE_OFFSET
        self.mem.buf[address:address + 4] = size.to_bytes(4, "little")

    async def acquire_read_lock(self):
        await self.acquire_lock(self.R_LOCK_POINTER)

    async def acquire_write_lock(self):
        await self.acquire_lock(self.W_LOCK_POINTER)

    async def acquire_lock(self, address):
        lock_pid = int.from_bytes(self.mem.buf[address:address + 4], "little")
        my_pid = os.getpid()
        start = time.time()
        while lock_pid != my_pid:
            lock_pid = int.from_bytes(self.mem.buf[address:address + 4], "little")
            if lock_pid == 0:
                self.mem.buf[address:address + 4] = my_pid.to_bytes(4, "little")
                lock_pid = int.from_bytes(self.mem.buf[address:address + 4], "little")
                if lock_pid == my_pid:
                    return
            elapsed = time.time() - start
            if elapsed > self.LOCK_TIMEOUT:
                raise TimeoutError
            await asyncio.sleep(self.LOCK_CHECK_INTERVAL)

    async def release_lock(self, address):
        self.mem.buf[address:address + 4] = bytearray(4)

    async def release_read_lock(self):
        await self.release_lock(self.R_LOCK_POINTER)

    async def release_write_lock(self):
        await self.release_lock(self.W_LOCK_POINTER)

    @property
    def free_space(self):
        if self.alloc_index < self.exe_index:
            return self.exe_index - self.alloc_index
        else:
            return self._data_size - (self.alloc_index - self.exe_index)

    @property
    def _data_size(self):
        return self.size - self.Q_CONTROL_SIZE

    @property
    def alloc_index(self):
        return int.from_bytes(self.mem.buf[self.ALLOC_POINTER:self.ALLOC_POINTER + 4], "little")

    @alloc_index.setter
    def alloc_index(self, val):
        self.mem.buf[self.ALLOC_POINTER:self.ALLOC_POINTER + 4] = val.to_bytes(4, "little")

    @property
    def exe_index(self):
        return int.from_bytes(self.mem.buf[self.EXE_POINTER:self.EXE_POINTER + 4], "little")

    @exe_index.setter
    def exe_index(self, val):
        self.mem.buf[self.EXE_POINTER:self.EXE_POINTER + 4] = val.to_bytes(4, "little")

    @property
    def exe_counter(self):
        return int.from_bytes(self.mem.buf[self.EXE_COUNTER_POINTER:self.EXE_COUNTER_POINTER + 4], "little")

    @exe_counter.setter
    def exe_counter(self, val):
        self.mem.buf[self.EXE_COUNTER_POINTER:self.EXE_COUNTER_POINTER + 4] = val.to_bytes(4, "little")

    @property
    def alloc_counter(self):
        return int.from_bytes(self.mem.buf[self.ALLOC_COUNTER_POINTER:self.ALLOC_COUNTER_POINTER + 4], "little")

    @alloc_counter.setter
    def alloc_counter(self, val):
        self.mem.buf[self.ALLOC_COUNTER_POINTER:self.ALLOC_COUNTER_POINTER + 4] = val.to_bytes(4, "little")

    @property
    def pending_counter(self):
        return self.alloc_counter - self.exe_counter

    @property
    def direction(self):
        return int.from_bytes(self.mem.buf[self.DIRECTION_POINTER:self.DIRECTION_POINTER + 1], "little")

    @direction.setter
    def direction(self, val: Q_DIRECTION):
        self.mem.buf[self.DIRECTION_POINTER:self.DIRECTION_POINTER + 1] = int(val).to_bytes(1, "little")

    @property
    def status(self):
        return int.from_bytes(self.mem.buf[self.STATUS_POINTER:self.STATUS_POINTER + 1], "little")

    @status.setter
    def status(self, val: LOCK_STATUS):
        self.mem.buf[self.STATUS_POINTER:self.STATUS_POINTER + 1] = int(val).to_bytes(1, "little")

    @property
    def api_def(self):
        return API_Queue(from_p=self.from_p, to_p=self.to_p, q_id=self.q_id, size=self.size, host=self.host)

    @property
    def status_str(self):
        return f"alloc count:{self.alloc_counter} , exe count: {self.exe_counter} , pending: {self.pending_counter}"
