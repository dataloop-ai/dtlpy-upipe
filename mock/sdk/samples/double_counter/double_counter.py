import asyncio

import mock.sdk as up
from mock.sdk.entities import Processor, Pipe,Queue

async def main():
    a = Processor('a', entry='a.py')
    b = Processor('b', entry='b.py')
    c = Processor('c', entry='c.py')
    pipe = Pipe('plus-one')
    a.add(c)
    pipe.add(a).add(b)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
