import asyncio


from mock.sdk.entities import Processor, Pipe,MemQueue

async def main():
    a = Processor('a', entry='a.py')
    b = Processor('b', entry='b.py')
    c = Processor('c', entry='c.py')
    pipe = Pipe('plus-one')
    pipe.add(a).add(c)
    pipe.add(b).add(c)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
