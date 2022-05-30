import asyncio

from dataloop.upipe import Process, DType


async def main():
    print("Hello a")
    me = Process("a")
    await me.join()
    print("a connected")
    val = 1
    while True:
        if await me.emit(val, DType.U32):

            if val % 10000 == 0:
                print(f"{val / 1000}K")
            if val == 15000:
                break
            val += 1


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print(" a Done")
