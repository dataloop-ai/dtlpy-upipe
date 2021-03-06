import asyncio

from dataloop.upipe import Pipe, Processor


async def main():
    limit = 50000
    config = {"limit": limit}
    a = Processor('a', entry='./a.py', config=config)
    b = Processor('b', entry='./b.py', config=config)
    pipe = Pipe('plus-one')
    pipe.add(a).add(b)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
