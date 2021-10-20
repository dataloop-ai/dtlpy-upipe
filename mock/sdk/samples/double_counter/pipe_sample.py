import asyncio

import mock.sdk as up


async def main():
    a = up.Processor('a', path='a.py')
    b = up.Processor('b', path='b.py')
    c = up.Processor('c', path='c.py')
    pipe = up.Pipe('plus-one')
    a.add(c)
    pipe.add(a).add(b)
    await pipe.start()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
