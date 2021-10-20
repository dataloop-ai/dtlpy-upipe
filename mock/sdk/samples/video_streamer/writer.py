import asyncio
import cv2
import mock.sdk as up
import time

from mock.sdk import DataFrame


def on_frame(frame: DataFrame):
    if frame.data is None:
        return
    cv2.imshow("result", frame.data)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return


async def main():
    print("Hello writer")
    proc = up.Processor("writer")
    proc.connect()
    proc.on_frame(on_frame)
    proc.start()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
