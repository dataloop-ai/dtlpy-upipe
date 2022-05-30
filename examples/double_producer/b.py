import asyncio

from dataloop.upipe import Process, DType


async def main():
    print("Hello b")
    me = Process("b")
    await me.join()
    print("b connected")
    val = 1
    while True:
        if await me.emit(val, DType.U32):

            if val % 10000 == 0:
                print(f"{val / 1000}K")
            if val == 100000:
                break
            val += 1


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print(" b Done")
