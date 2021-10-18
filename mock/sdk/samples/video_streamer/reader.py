import cv2
import asyncio

import mock.sdk as up


async def main():
    me = up.Processor("reader")
    me.connect()
    print("a connected")
    cap = cv2.VideoCapture(r"E:\TypesExamples\surfer.webm")
    i_frame = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (32,32))
        if await me.emit(frame, up.DType.ND_ARR):
            i_frame += 1
            if i_frame % 10 == 0:
                print(f"{i_frame}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
