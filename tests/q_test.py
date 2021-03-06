import asyncio

import numpy as np

import upipe.types
from upipe.entities import DataFrame, DType
from upipe.entities.mem_queue import MemQueue


async def test_throughput(count: int):
    q = MemQueue(upipe.types.APIQueue(name="test_throughput",
                                      from_p="a",
                                      to_p="b",
                                      id="12",
                                      size=4000))
    for i in range(count):
        frame = DataFrame(i)
        if i == 65818:
            print("here i am")
        if i % 10000 == 0:
            print(f"{i / 1000}K")
        if await q.put(frame):
            out: DataFrame = await q.get()
            if not out:
                q.print()
                raise MemoryError
            if out.data != i:
                q.print()
                raise ValueError
        else:
            q.print()
            raise IndexError


async def test_json(count: int = 10):
    q = MemQueue(upipe.types.APIQueue(name="test_json",
                                      from_p="a",
                                      to_p="b",
                                      id="12",
                                      size=4096))
    for i in range(count):
        frame = DataFrame({"counter": i})
        if await q.put(frame):
            print(f"{i} json write")
            out: DataFrame = await q.get()
            if not out:
                q.print()
                raise MemoryError
            if not out.data:
                q.print()
                raise ValueError
            if out.data["counter"] != i:
                q.print()
                raise KeyError
            print(f"{i} json read")
        else:
            q.print()
            raise IndexError


async def test_str(count: int = 10):
    q = MemQueue(upipe.types.APIQueue(name="test_str",
                                      from_p="a",
                                      to_p="b",
                                      id="12",
                                      size=200))
    for i in range(count):
        frame = DataFrame(f"{i}")
        frame.set_pipe_exe_id()
        if await q.put(frame):
            print(f"{i} str write")
            out: DataFrame = await q.get()
            if not out:
                q.print()
                raise MemoryError
            if int(out.data) != i:
                q.print()
                raise ValueError
            if out.pipe_execution_id != frame.pipe_execution_id:
                raise ValueError("Executing id mismatch")
            print(f"{i} str read")
        else:
            q.print()
            raise IndexError


async def test_serial(d_type: DType = DType.U8):
    q = MemQueue(upipe.types.APIQueue(name="test_serial",
                                      from_p="a",
                                      to_p="b",
                                      id="12",
                                      size=4096))
    for i in range(10):
        frame = DataFrame(i)
        if await q.put(frame):
            print(f"{i} write")
            out: DataFrame = await q.get()
            if not out:
                q.print()
                raise MemoryError
            if out.data != i:
                q.print()
                raise ValueError
            print(f"{i} read")
        else:
            q.print()
            raise IndexError


async def test_arr(count: int = 100):
    q = MemQueue(upipe.types.APIQueue(name="test_arr",
                                      from_p="a",
                                      to_p="b",
                                      id="12",
                                      size=2341))
    for i in range(count):
        frame = DataFrame([i, i + 1, f"{i}", {"i": i}])
        if await q.put(frame):
            print(f"write array" + str([i, i + 1, f"{i}", {"i": i}]))
            out: DataFrame = await q.get()
            if not out:
                q.print()
                raise MemoryError
            if out.data[0] != i or out.data[1] != i + 1 or out.data[2] != f"{i}" or out.data[3]["i"] != i:
                q.print()
                raise ValueError
            print(f"{i} read")
        else:
            q.print()
            raise IndexError


async def test_tuple(count: int = 100):
    q = MemQueue(upipe.types.APIQueue(name="test_tuple",
                                      from_p="a",
                                      to_p="b",
                                      id="12",
                                      size=2341))
    for i in range(count):
        frame = DataFrame((i, i + 1, f"{i}", {"i": i}))
        if await q.put(frame):
            print(f"write tuple " + str((i, i + 1, f"{i}", {"i": i})))
            out: DataFrame = await q.get()
            if not out:
                q.print()
                raise MemoryError
            if out.data[0] != i or out.data[1] != i + 1 or out.data[2] != f"{i}" or out.data[3]["i"] != i:
                q.print()
                raise ValueError
            print(f"{i} read")
        else:
            q.print()
            raise IndexError


async def test_nd_array(count: int = 100):
    q = MemQueue(upipe.types.APIQueue(name="test_nd_array",
                                      from_p="a",
                                      to_p="b",
                                      id="12",
                                      size=2341))
    for i in range(count):
        arr = np.random.rand(i % 5, i % 30)
        frame = DataFrame(arr)
        if await q.put(frame):
            print(f"write nd_arr " + str((i, i + 1, f"{i}", {"i": i})))
            out: DataFrame = await q.get()
            if not out:
                q.print()
                raise MemoryError
            if not np.array_equal(arr, out.data):
                q.print()
                raise ValueError
            print(f"{i} read")
        else:
            q.print()
            raise IndexError


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_serial(DType.U8))
    loop.run_until_complete(test_nd_array())
    loop.run_until_complete(test_tuple())
    loop.run_until_complete(test_arr())
    loop.run_until_complete(test_json())
    loop.run_until_complete(test_str(10 ** 4))
    loop.run_until_complete(test_throughput(10 ** 5))
    loop.run_until_complete(test_serial(DType.U64))
