import asyncio

import upipe as up
from upipe import Processor, Pipe, MemQueue


async def main():
    print("Hello b")
    me = Processor("b")
    await me.connect()
    print("b connected")
    val = 1
    q: MemQueue = me.get_next_q_to_emit()
    while True:
        if await me.emit(val, up.DType.U32):

            if val % 10000 == 0:
                print(f"{val / 1000}K")
            if val == 100000:
                break
            val += 1


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print(" b Done")