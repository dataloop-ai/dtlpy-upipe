import asyncio

import mock.sdk as up
from mock.sdk import Queue


async def main():
    print("Hello b")
    me = up.Processor("b")
    await me.connect()
    print("b started")
    val = 1
    q: Queue = me.get_next_q_to_emit()
    while True:
        if await me.emit(val, up.DType.U32):
            val += 1
            if val % 10000 == 0:
                print(f"{val / 1000}K")
                print(f"{val / 1000}K")
            if val % 100000 == 0:
                break


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
