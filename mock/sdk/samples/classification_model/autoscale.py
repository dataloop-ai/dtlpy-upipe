import asyncio

from mock.sdk.entities import Processor, Pipe


async def main():
    a = Processor('reader', entry="reader.py")
    b = Processor('classifier', entry="classifier.py", autoscale=10)
    pipe = Pipe('classification')
    pipe.add(a).add(b)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
