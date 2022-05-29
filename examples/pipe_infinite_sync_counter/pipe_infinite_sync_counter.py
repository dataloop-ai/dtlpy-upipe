import asyncio

from upipe import Processor, Process, Pipe

limit = 100000


async def plus_plus():
    print("Hello plus_plus")
    proc = Process("plus_plus")
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
    a = Processor('plus_plus', func=plus_plus)
    pipe = Pipe('plus-one-pipe')
    pipe.add(a)
    await pipe.load()
    await pipe.start()
    counter = 0
    print("Pending pipe start")
    while True:
        if pipe.running:
            counter = await pipe.emit_sync(counter, timeout_ms=-1)
            if counter % 100 == 0 and counter > 0:
                print(f"from main: {counter / 1000}K")
        else:
            await asyncio.sleep(.1)
        if pipe.pending_termination:
            break
    await pipe.wait_for_completion()
    print(f"Pipe done: {counter / 1000}K")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
