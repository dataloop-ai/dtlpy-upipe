import asyncio
# import time
# time.sleep(20)
from upipe.entities import MemQueue, Processor, DType


async def main():
    print("Hello a")
    me = Processor("a")
    await me.connect()
    limit = me.config['limit']
    print("a connected")
    val = 1
    q: MemQueue = me.get_next_q_to_emit()
    while True:
        if await me.emit(val, DType.U32):

            if val % 10000 == 0:
                print(f"{val / 1000}K")
            if val == limit:
                break
            val += 1


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print(" a Done")
