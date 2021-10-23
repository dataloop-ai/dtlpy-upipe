import asyncio
from threading import Thread
from mock.sdk.entities import Queue, Processor

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
        if counter == 400:
            break
        if counter % 25 == 0:
            print(f"Displaying frame {counter}")
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

    proc = Processor('display.py')
    await proc.connect()
    proc.start()
    print("started")
    frame_cnt = 0
    while True:
        if frame_cnt == 400:
            break
        display_frame = await proc.get_sync()
        frame_cnt += 1
    print("Display done")


if __name__ == "__main__":
    thread = Thread(target=display_thread)
    thread.start()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
