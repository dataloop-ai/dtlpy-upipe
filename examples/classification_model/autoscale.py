import asyncio
from dataloop.upipe import Processor, Pipe, types


async def main():
    a = Processor('reader', entry="reader.py")
    b = Processor('classifier', entry="classifier.py", settings=types.APIProcSettings(autoscale=1))
    pipe = Pipe('classification')
    pipe.add(a).add(b)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
