import asyncio
from dataloop import upipe


async def main():
    a = upipe.Processor('a', entry="a.py")
    b = upipe.Processor('b', entry="b.py", settings=upipe.types.APIProcSettings(autoscale=8))
    pipe = upipe.Pipe('plus-one')
    pipe.add(a).add(b)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
