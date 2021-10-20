import asyncio
import sys

import mock.sdk as up
import time

from mock.sdk import DataFrame, Queue


async def main():
    print("Hello b")
    proc = up.Processor("b")
    await proc.connect()
    proc.start()
    print("b started")
    first = True
    q: Queue = proc.get_next_q_to_process()
    while True:
        try:
            counter = await proc.get_sync()
            if counter + 1 != q.exe_counter:
                raise IndexError("Q counter mismatch ")
            if first:
                first = False
                print("b got first message")
                sys.stdout.flush()
        except TimeoutError:
            print("timeout")
            break
        if counter % 1000 == 0:
            print(f"{float(counter / 1000)}K")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
