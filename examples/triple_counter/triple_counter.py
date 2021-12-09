import asyncio
import upipe as up
from upipe import Processor, Pipe


async def a():
    print("Hello a")
    me = Processor("a")
    await me.connect()
    print("a connected")
    val = 1
    while True:
        if await me.emit(val, up.DType.U32):
            if val % 10000 == 0:
                print(f"{val / 1000}K")
            if val == 100000:
                break
            val += 1


async def b():
    print("Hello b")
    proc = Processor("b")
    await proc.connect()

    proc.start()
    while True:
        counter = await proc.get_sync()
        if await proc.emit(counter, up.DType.U32):
            if counter % 10000 == 0:
                print(f"{counter / 1000}K")
            if counter == 100000:
                break


async def c():
    print("Hello c")
    proc = Processor("c")
    await proc.connect()

    proc.start()
    while True:
        counter = await proc.get_sync()
        if await proc.emit(counter, up.DType.U32):
            if counter % 10000 == 0:
                print(f"{counter / 1000}K")
            if counter == 100000:
                break


async def main():
    aa = Processor('a', func=a)
    bb = Processor('b', func=b)
    cc = Processor('c', func=c)
    pipe = Pipe('plus-one')
    pipe.add(aa).add(bb).add(cc)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Done")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
