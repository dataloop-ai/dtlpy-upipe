import asyncio

from dataloop.upipe import MemQueue, Worker


async def main():
    print("Hello b")
    proc = Worker("b")
    await proc.join()
    limit = proc.config['limit']
    counter = 0
    while True:
        try:
            counter = await proc.get_sync()
            if counter == limit:
                break
            q: MemQueue = proc.in_qs[0]
            if counter != q.exe_counter:
                raise BrokenPipeError(f"Execution error: counter {counter}, executed {q.exe_counter}")
        except TimeoutError:
            print("timeout")
            break
        if counter % 10000 == 0:
            print(f"{counter / 1000}K")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print("b Done")
