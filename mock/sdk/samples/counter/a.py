import asyncio

import mock.sdk as up


async def main():
    print("Hello a")
    me = up.Processor("a")
    me.connect()
    print("a connected")
    val = 1
    while True:
        if await me.emit(val, up.DType.U32):
            val += 1
            if val % 10000 == 0:
                print(f"{val / 1000}K")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
