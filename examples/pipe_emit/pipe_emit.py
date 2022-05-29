import asyncio
from threading import Thread
from upipe import Processor, Process, Pipe, types

LIMIT = 10000


async def first():
    print("loading first")
    me = Process("first")
    await me.join()
    print("first connected")
    while True:
        msg = await me.get()
        if msg is None:
            continue
        print(f'got msg: {msg}')
        if msg % 100 == 0:
            print(f"{msg / 1000}K")
        if msg > LIMIT:
            break
    print('------------------success------------------')


async def main():
    proc = Processor('first', func=first)
    pipe = Pipe('emit-pipe')
    pipe.add(proc)
    await pipe.start()
    p = Thread(target=to_run, args=(pipe,))
    p.start()
    await pipe.wait_for_completion()
    print("Running")


def to_run(pipe: Pipe):
    while True:
        if pipe.running:
            break

    print('------------ Start emitting to pipe ------------ ')
    for val in range(1000000):
        _ = asyncio.run(pipe.emit(val))
        if val % 100 == 0:
            print(f"from main: {val / 1000}K")
        if val > LIMIT:
            break


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
