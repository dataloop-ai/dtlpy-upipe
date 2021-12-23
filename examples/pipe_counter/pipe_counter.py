import asyncio

from upipe import Processor, Pipe, DType

limit = 100000


async def processor_a():
    global limit
    print("Hello embedded processor a")
    me = Processor("a")
    await me.connect()
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
    proc = Processor("b")
    await proc.connect()
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


async def plus_plus():
    print("Hello plus_plus")
    proc = Processor("b")
    await proc.connect()
    while True:
        counter = await proc.get_sync()
        counter += 1
        proc.emit(counter)
        if counter % 1000 == 0:
            print(f"{counter / 1000}K")
    print("embedded processor plus_plus completed")


async def main():
    a = Processor('a', func=plus_plus)
    pipe = Pipe('plus-one')
    pipe.add(a)
    await pipe.start()
    counter = 0
    print("Running")
    while pipe.running:
        counter = await pipe.emit(counter)
        if counter % 1000 == 0:
            print(f"{counter / 1000}K")
        if counter > 5000 == 0:
            print(f"Done : {counter / 1000}K")
            return
    pipe.terminate()
    pipe.wait_for_completion()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
