import asyncio

from upipe import MemQueue, Processor


async def main():
    print("Hello b")
    proc = Processor("b")
    await proc.connect()

    proc.start()
    counter = 0
    while True:
        try:
            q: MemQueue = proc.in_qs[0]
            counter = await proc.get_sync()
            if counter == 15000:
                break

            if counter != q.exe_counter:
                raise BrokenPipeError(f"Execution error: counter {counter}, executed {q.exe_counter}")
        except TimeoutError:
            print("timeout")
            break
        if counter % 1000 == 0:
            print(f"{counter / 1000}K")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print("b Done")
