import asyncio

from mock.sdk.entities import Processor, Pipe


async def main():

    a = Processor('a', entry='a.py')
    b = Processor('b', entry='b.py')
    pipe = Pipe('plus-one')
    pipe.add(a).add(b)
    await pipe.start()
    print("Running")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
