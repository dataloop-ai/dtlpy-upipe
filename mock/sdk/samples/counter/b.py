import asyncio

import mock.sdk as up
import time

from mock.sdk import DataFrame, Queue


async def main():
    print("Hello b")
    proc = up.Processor("b")
    await proc.connect()

    proc.start()
    while True:
        try:
            counter = await proc.get_sync()
            q: Queue = proc.in_qs[0]
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
    loop.run_forever()
