import asyncio

from dataloop.upipe import Processor, Worker, Pipe, DType

limit = 10000


async def processor_a():
    global limit
    print("Hello embedded processor a")
    me = Worker()
    await me.join()
    print("a connected")
    val = 1
    while True:
        if await me.emit(val, DType.U32):
            if val % 1000 == 0:
                print(f"{val / 1000}K")
            if val == limit:
                break
            val += 1
        else:
            print('failed')
    print("a done")


async def processor_b():
    global limit
    print("Hello embedded processor b")
    proc = Worker()
    await proc.join()
    while True:
        try:
            counter = await proc.get_sync()
            if counter == limit:
                break
        except TimeoutError:
            print("timeout")
            break
        if counter % 1000 == 0:
            print(f"{counter / 1000}K")
    print("embedded processor b completed")


async def main():
    a = Processor('a', func=processor_a)
    b = Processor('b', func=processor_b)
    pipe = Pipe('plus-one')
    pipe.add(a).add(b)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
