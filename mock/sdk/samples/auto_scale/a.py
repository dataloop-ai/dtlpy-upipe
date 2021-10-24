import asyncio
from mock.sdk.entities import Queue, Processor, DType

limit = 10000
async def main():
    global limit
    print("Hello stressor a")
    me = Processor("a")
    await me.connect()
    print("a connected")
    val = 1
    while True:
        if await me.emit(val, DType.U32):
            if val % 1000 == 0:
                print(f"{val / 1000}K")
            if val == limit:
                break
            val += 1
    print("a done")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print(" a Done")
