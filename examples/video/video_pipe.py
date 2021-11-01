import asyncio
from upipe import Processor, Pipe, MemQueue


async def main():
    a = Processor('reader.py')
    b = Processor('display.py')
    pipe = Pipe('plus-one')
    pipe.add(a).add(b)
    await pipe.start()
    print("Running")
    await pipe.wait_for_completion()
    print("Video reader waiting")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
