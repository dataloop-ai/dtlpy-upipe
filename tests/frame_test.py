import asyncio

import numpy as np

import upipe.types
from upipe.entities import DataFrame, DType
from upipe.entities.dataframe import DataField
from upipe.entities.mem_queue import MemQueue
async def test_field_int():
    field = DataField(f"{1}", 1)
    field2 = DataField.from_byte_arr(field.byte_arr)
    for i in range(10):
        field = DataField(f"{i}", i)
        field2 = DataField.from_byte_arr(field.byte_arr)
        if field.value != i:
            raise ValueError(f"Int Value was not recovered from data field:{i}")
        if field.key != f"{i}":
            raise KeyError(f"Int Key was not recovered from data field:{i}")

async def test_int():
    frame = DataFrame(1)
    frame2 = DataFrame.from_byte_arr(frame.byte_arr)
    for i in range(10):
        frame = DataFrame(i)
        frame2 = DataFrame.from_byte_arr(frame.byte_arr)
        if frame2.data != i:
            raise ValueError(f"Integer was not recovered from data frame:{i}")

async def test_nd_array(count: int = 100):
    for i in range(count):
        arr = np.random.rand(i % 5, i % 30)
        frame = DataFrame(arr)
        frame2 = DataFrame.from_byte_arr(frame.byte_arr)
        if not np.array_equal(arr, frame2.data):
            raise ValueError(f"ND Array was not recovered from data frame:{i}")

async def test_tuple(count: int = 100):
    for i in range(count):
        tp = (i, i + 1, f"{i}", {"i": i})
        frame = DataFrame(tp)
        frame2 = DataFrame.from_byte_arr(frame.byte_arr)
        if frame2.data[0] != i or frame2.data[1] != i + 1 or frame2.data[2] != f"{i}" or frame2.data[3]["i"] != i:
            raise ValueError(f"Tuple was not recovered from data frame:{i}")

async def test_arr(count: int = 100):
    for i in range(count):
        arr = [i, i + 1, f"{i}", {"i": i}]
        frame = DataFrame(arr)
        frame2 = DataFrame.from_byte_arr(frame.byte_arr)
        if frame2.data[0] != i or frame2.data[1] != i + 1 or frame2.data[2] != f"{i}" or frame2.data[3]["i"] != i:
            raise ValueError(f"Array was not recovered from data frame:{i}")

async def test_json(count: int = 10):
    for i in range(count):
        js = {"counter": i}
        frame = DataFrame(js)
        frame2 = DataFrame.from_byte_arr(frame.byte_arr)
        if frame2.data["counter"] != i:
            raise ValueError(f"JSON was not recovered from data frame:{i}")

async def test_str(count: int = 10):
    for i in range(count):
        test_string = f"{i}"
        frame = DataFrame(test_string)
        frame2 = DataFrame.from_byte_arr(frame.byte_arr)
        if int(frame2.data) != i:
            raise ValueError(f"STRING was not recovered from data frame:{i}")













if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_field_int())
    loop.run_until_complete(test_int())
    loop.run_until_complete(test_nd_array())
    loop.run_until_complete(test_tuple())
    loop.run_until_complete(test_arr())
    loop.run_until_complete(test_json())
    loop.run_until_complete(test_str(10 ** 4))
