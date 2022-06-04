import asyncio

from dataloop.upipe import Processor, Worker, Pipe

limit = 100000


async def plus_plus():
    print("Hello plus_plus")
    proc = Worker("plus_plus_processor")
    await proc.join()
    while True:
        counter = await proc.get()
        if counter is None:
            continue
        counter += 1
        while not await proc.emit(counter):
            continue
        if counter % 100 == 0:
            print(f"from proc: {counter / 1000}K")


async def main():
    a = Processor('plus_plus_processor', func=plus_plus)
    pipe = Pipe('plus-one-pipe')
    pipe.add(a)
    await pipe.start()
    val = await pipe.sink_q.get()
    counter = 0
    val = await pipe.emit_sync(counter)
    print(f"First inc:{val}")
    val = await pipe.emit_sync(val)
    print(f"Second inc:{val}")
    print("Running")
    while pipe.running:
        counter = await pipe.emit_sync(counter)
        if counter % 100 == 0 and counter > 0:
            print(f"from main: {counter / 1000}K")
        if counter > 5000 == 0:
            print(f"Done : {counter / 1000}K")
            break
    await pipe.terminate()
    await pipe.wait_for_completion()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
