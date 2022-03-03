import binascii
import os
import struct

import numpy as np
import time
from enum import IntEnum
from multiprocessing import shared_memory

from pydantic.class_validators import Optional
from pydantic.main import BaseModel
from typing import List, Union

from ..types import APIQueue
from .dataframe import DataFrame

import asyncio

from ..types.performance import QueuePerformanceStats, PerformanceMetric, ThroughputPerformanceMetric

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
        self._enqueue_log: List[QLogEntry] = []
        self._dequque_log: List[QLogEntry] = []
        self.entry_limit = entry_limit

    def add_to_log(self, entry: QLogEntry, log: list):
        while len(log) > self.entry_limit:
            log.remove(log[0])
        log.append(entry)

    def log_enqueue(self, entry: QLogEntry):
        self.add_to_log(entry, self._enqueue_log)

    def log_dequeue(self, entry: QLogEntry):
        self.add_to_log(entry, self._dequque_log)

    @property
    def pending_stats(self):
        if len(self._dequque_log) == 0:
            return 0
        return int(np.mean([d.pending_counter for d in self._dequque_log]))


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
        self.frame_status_pointer = exe_index + MemQueue.FRAME_STATUS_OFFSET
        self.frame_status = buffer[self.frame_status_pointer]
        self.frame_d_type = buffer[exe_index + MemQueue.FRAME_TYPE_OFFSET]
        self.frame_size_pointer = exe_index + MemQueue.FRAME_SIZE_OFFSET
        self.frame_size = int.from_bytes(buffer[self.frame_size_pointer:self.frame_size_pointer + 4], "little")
        self.frame_data_pointer = exe_index + MemQueue.FRAME_HEADER_SIZE
        self.frame_data_size = self.frame_size - MemQueue.FRAME_HEADER_SIZE
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


class MemQueue:
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
    R_LOCK__COUNTER_POINTER = 10  # size = 4
    W_LOCK_POINTER = 14  # size = 4
    W_LOCK__COUNTER_POINTER = 20  # size = 4
    STATUS_POINTER = 24  # size = 1
    DIRECTION_POINTER = 25  # size = 1
    ALLOC_POINTER = 26  # size = 4
    EXE_POINTER = 30  # size = 4
    ALLOC_COUNTER_POINTER = 34  # size = 4
    EXE_COUNTER_POINTER = 38  # size = 4
    DFPS_CALC_INTERVAL = 42  # size = 4
    LAST_DFPS_CALC_TIME = 46  # size = 8
    DFPS_LAST_ALLOC_COUNTER = 54  # size = 4
    DFPS_LAST_EXE_COUNTER = 58  # size = 4
    # end of Q header
    LOCK_TIMEOUT = 100
    LOCK_CHECK_INTERVAL = 0.05
    MAX_CAPACITY = 0.90
    WATER_MARK = bytearray()
    WATER_MARK.extend(map(ord, "d@tal0op"))

    @staticmethod
    def allocate_id():
        q_id = MemQueue.next_serial
        MemQueue.next_serial += 1
        return q_id

    def __init__(self, q: APIQueue):
        self.log: QActionLog = QActionLog()
        min_q_size = self.Q_CONTROL_SIZE + self.FRAME_HEADER_SIZE + 1  # send at least 1 byte ...
        if q.size < min_q_size:
            raise MemoryError(f"Queue size must be at least {min_q_size}")
        self.frame_counter = 0
        self.qid = q.id
        self.from_p = q.from_p
        self.to_p = q.to_p
        self.length = 10
        self.name = f"{self.from_p} -> {self.to_p} ({self.qid})"
        self.memory_name = f"Q_{self.qid}"
        self.size = q.size
        self.nextMessageAddress = 0
        self.currentAddress = 0
        self.host = q.host
        self.r_lock_mem = None
        self.w_lock_mem = None
        try:
            self.mem = shared_memory.SharedMemory(name=self.memory_name, create=True, size=self.size)
            self.mem.buf[:] = bytearray(self.size)
            self.status = LOCK_STATUS.OPEN
            self.direction = Q_DIRECTION.NORMAL
            self.alloc_index = self.DATA_START_POINT
            self.exe_index = self.DATA_START_POINT

        except FileExistsError:
            self.mem = shared_memory.SharedMemory(name=self.memory_name, size=self.size)
        self.dfps_interval_ms = 1000

    def log_enqueue(self, entry: QLogEntry):
        current_time = time.time() * 1000  # ms
        entry.time = current_time
        self.log.log_enqueue(entry)

    def log_dequeue(self, entry: QLogEntry):
        current_time = time.time() * 1000  # ms
        entry.time = current_time
        self.log.log_dequeue(entry)

    def update_dfps(self):
        current_time_ms = time.time() * 1000
        last_dfps_update_time = self.last_dfps_calc_time
        dfps_interval = self.dfps_interval_ms
        if current_time_ms - last_dfps_update_time < dfps_interval:
            return
        self.dfps_last_exe_counter = self.exe_counter
        self.dfps_last_alloc_counter = self.alloc_counter
        self.last_dfps_calc_time = int(current_time_ms)

    async def get(self) -> Union[DataFrame, None]:
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
            self.log_dequeue(
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
            frame = DataFrame.from_byte_arr(frame_data)
            self.update_dfps()
            self.exe_counter += 1
            return frame
        finally:
            self.release_read_lock()

    async def space_available(self, frame: DataFrame):
        frame_size = len(frame.to_byte_arr())
        frame_size = frame_size + self.FRAME_HEADER_SIZE
        if frame_size > self.free_space:
            return False
        return True

    async def put(self, df: DataFrame):
        capacity = (self.size - self.Q_CONTROL_SIZE - self.free_space) / self.size
        if capacity > self.MAX_CAPACITY:
            return False
        body = df.to_byte_arr()
        frame_size = len(body) + self.FRAME_HEADER_SIZE
        if frame_size > self.free_space:
            return False
        if self.alloc_index == 2765604:
            pass
        debug_print(
            f"Put {current_milli_time()} - Frame size:{frame_size}, free space:{self.free_space}, alloc_index:{self.alloc_index},exe_index:{self.exe_index}")
        try:
            await self.acquire_write_lock()
            header = bytearray(self.FRAME_HEADER_SIZE)
            header[self.FRAME_STATUS_OFFSET] = FRAME_STATUS.CREATED
            header[self.FRAME_TYPE_OFFSET] = 13  # for luck, not needed for now
            header[self.FRAME_SIZE_OFFSET:self.FRAME_SIZE_OFFSET + 4] = frame_size.to_bytes(4, "little")
            header[self.FRAME_WATERMARK_OFFSET:self.FRAME_WATERMARK_OFFSET + 8] = self.WATER_MARK
            header[self.FRAME_CRC32_OFFSET:self.FRAME_CRC32_OFFSET + 4] = binascii.crc32(body).to_bytes(4, "little")
            header[self.FRAME_NUM_OFFSET:self.FRAME_NUM_OFFSET + 4] = self.frame_counter.to_bytes(4, "little")
            self.log_enqueue(
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
            self.update_dfps()
            self.alloc_counter += 1
            return True
        finally:
            self.release_write_lock()

    def print(self):
        return
        # parser = FrameParser(self.mem.buf, self.exe_index)
        # parser.print()

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
        self.r_lock_mem = await self.acquire_lock(self.r_lock_memory_name)

    async def acquire_write_lock(self):
        self.w_lock_mem = await self.acquire_lock(self.w_lock_memory_name)

    async def acquire_lock(self, lock_name):
        start = time.time()
        attempts = 0
        while True:
            attempts += 1
            try:
                lock_mem = shared_memory.SharedMemory(name=lock_name, create=True, size=1)
                return lock_mem
            except FileExistsError:
                await asyncio.sleep(self.LOCK_CHECK_INTERVAL)
            elapsed = time.time() - start
            if elapsed > self.LOCK_TIMEOUT + attempts * self.LOCK_CHECK_INTERVAL / 2:
                raise TimeoutError

    def release_read_lock(self):
        if not self.r_lock_mem:
            return
        self.r_lock_mem.close()
        self.r_lock_mem = None

    def release_write_lock(self):
        if not self.w_lock_mem:
            return
        self.w_lock_mem.close()
        self.w_lock_mem = None

    def get_32b_int(self, address):
        return int.from_bytes(self.mem.buf[address:address + 4], "little")

    def set_32b_int(self, address, value):
        self.mem.buf[address:address + 4] = value.to_bytes(4, "little")

    def get_64b_int(self, address):
        return int.from_bytes(self.mem.buf[address:address + 8], "little")

    def set_64b_int(self, address, value):
        self.mem.buf[address:address + 8] = value.to_bytes(8, "little")

    def get_32b_float(self, address):
        return struct.unpack("f", self.mem.buf[address:address + 4])[0]

    def set_32b_float(self, address, value):
        self.mem.buf[address:address + 4] = bytearray(struct.pack('f', value))

    @property
    def id(self):
        return self.qid

    @property
    def dfps_interval_ms(self):
        return self.get_32b_int(self.DFPS_CALC_INTERVAL)

    @dfps_interval_ms.setter
    def dfps_interval_ms(self, val):
        self.set_32b_int(self.DFPS_CALC_INTERVAL, val)

    @property
    def last_dfps_calc_time(self):
        return self.get_64b_int(self.LAST_DFPS_CALC_TIME)

    @last_dfps_calc_time.setter
    def last_dfps_calc_time(self, val):
        self.set_64b_int(self.LAST_DFPS_CALC_TIME, val)

    @property
    def dfps_last_alloc_counter(self):
        return self.get_32b_int(self.DFPS_LAST_ALLOC_COUNTER)

    @dfps_last_alloc_counter.setter
    def dfps_last_alloc_counter(self, val):
        self.set_32b_int(self.DFPS_LAST_ALLOC_COUNTER, val)

    @property
    def dfps_last_exe_counter(self):
        return self.get_32b_int(self.DFPS_LAST_EXE_COUNTER)

    @dfps_last_exe_counter.setter
    def dfps_last_exe_counter(self, val):
        self.set_32b_int(self.DFPS_LAST_EXE_COUNTER, val)

    @property
    def dfps_in(self):
        dfps_calc_time_delta = time.time() * 1000 - self.last_dfps_calc_time
        return (self.alloc_counter - self.dfps_last_alloc_counter) / (dfps_calc_time_delta / 1000)

    @property
    def dfps_out(self):
        dfps_calc_time_delta = time.time() * 1000 - self.last_dfps_calc_time
        return (self.exe_counter - self.dfps_last_exe_counter) / (dfps_calc_time_delta / 1000)

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

    @property
    def w_lock_memory_name(self):
        return f"{self.memory_name}_wlock"

    @property
    def r_lock_memory_name(self):
        return f"{self.memory_name}_rlock"

    @status.setter
    def status(self, val: LOCK_STATUS):
        self.mem.buf[self.STATUS_POINTER:self.STATUS_POINTER + 1] = int(val).to_bytes(1, "little")

    @property
    def queue_def(self):
        return APIQueue(name=self.name,
                        from_p=self.from_p,
                        to_p=self.to_p,
                        id=self.qid,
                        size=self.size,
                        host=self.host)

    @property
    def status_str(self):
        return f"alloc count:{self.alloc_counter} , exe count: {self.exe_counter} , pending: {self.pending_counter}"

    def stats(self) -> QueuePerformanceStats:
        return QueuePerformanceStats(dfps_in=ThroughputPerformanceMetric(value=self.dfps_in),
                                     dfps_out=ThroughputPerformanceMetric(value=self.dfps_out),
                                     allocation_counter=PerformanceMetric(value=self.alloc_counter),
                                     exe_counter=PerformanceMetric(value=self.exe_counter),
                                     pending_counter=PerformanceMetric(value=self.pending_counter),
                                     allocation_index=PerformanceMetric(value=self.alloc_index),
                                     exe_index=PerformanceMetric(value=self.exe_index),
                                     free_space=PerformanceMetric(value=self.free_space),
                                     size=PerformanceMetric(value=self._data_size),
                                     q_id=self.id)
