import asyncio
from dataloop.upipe import MemQueue, Worker


async def main():
    print("Hello a")
    me = Worker("a")
    await me.join()
    limit = me.config['limit']
    print("a connected")
    val = 1
    q: MemQueue = me._get_next_q_to_emit()
    while True:
        if await me.emit(val):
            if val % 10000 == 0:
                print(f"{val / 1000}K")
            if val == limit:
                break
            val += 1


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print(" a Done")
