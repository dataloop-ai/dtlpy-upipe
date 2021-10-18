import asyncio
from threading import Thread

import mock.sdk as up
import time

from mock.sdk import DataFrame
import cv2

counter = 0
display_frame = None


def display_thread():
    global display_frame, counter
    cv2.namedWindow("video", cv2.WINDOW_AUTOSIZE)
    while True:
        if display_frame is not None:
            cv2.imshow("video", display_frame)
            display_frame = None
            counter += 1
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break
        time.sleep(.01)


async def main():
    global display_frame
    print("Hello display")

    proc = up.Processor('display.py')
    proc.connect()
    proc.start()
    print("started")
    while True:
        display_frame = await proc.get_sync()


if __name__ == "__main__":
    thread = Thread(target=display_thread)
    thread.start()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
