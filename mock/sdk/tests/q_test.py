import asyncio

from mock.sdk import DataFrame, DType
from mock.sdk.mem_queue import Queue


async def test_throughput(count: int):
    q = Queue("a", "b", "12", size=4000)
    for i in range(count):
        frame = DataFrame(i, DType.U32)
        if i == 65818:
            print("here i am")
        if i % 10000 == 0:
            print(f"{i/1000}K")
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


async def test_serial(type: DType = DType.U8):
    q = Queue("a", "b", "12",size=101)
    for i in range(10):
        frame = DataFrame(i, type)
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


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_throughput(10**9))
    #loop.run_until_complete(test_serial(DType.U64))
    #loop.run_until_complete(test_serial(DType.U8))