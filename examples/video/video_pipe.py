import asyncio
from upipe import Processor, Pipe


async def main():
    a = Processor('reader', entry='reader.py')
    b = Processor('display', entry='display.py')
    pipe = Pipe('plus-one')
    pipe.add(a).add(b)
    await pipe.start()
    print("Running")
    await pipe.wait_for_completion()
    print("Video reader waiting")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
