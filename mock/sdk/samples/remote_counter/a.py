import asyncio

import mock.sdk as up
from mock.sdk.entities import MemQueue, Processor


async def main():
    print("Hello a")
    me = Processor("a")
    await me.connect()
    print("a connected")
    val = 1
    q: MemQueue = me.get_next_q_to_emit()
    if q.alloc_counter != 0:
        raise BrokenPipeError("Queue already filled")
    while True:
        if await me.emit(val, up.DType.U32):

            if val % 10000 == 0:
                print(f"{val / 1000}K")
            if val == 15000:
                break
            val += 1


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print(" a Done")
