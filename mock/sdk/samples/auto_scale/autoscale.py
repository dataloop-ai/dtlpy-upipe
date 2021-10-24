import asyncio
import random
import string

from mock.sdk.entities import Processor, Pipe, DType
import hashlib


async def main():
    a = Processor('a', entry="a.py")
    b = Processor('b', entry="b.py", autoscale=10)
    pipe = Pipe('plus-one')
    pipe.add(a).add(b)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
