import asyncio

import mock.sdk as up
import time

from mock.sdk import DataFrame


def on_frame(frame:DataFrame):
    val = frame.data
    if val % 10000 == 0:
        print(f"{val / 1000}K")
    #proc.emit(data+1)


async def main():
    print("Hello b")
    proc = up.Processor("b")
    proc.connect()
    proc.on_frame(on_frame)
    proc.start()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
