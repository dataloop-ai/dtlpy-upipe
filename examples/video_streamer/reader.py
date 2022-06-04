import cv2
import asyncio
import os
from dataloop.upipe import Worker, DType


async def main():
    me = Worker("reader")
    await me.join()
    print("a connected")
    cap = cv2.VideoCapture(os.path.join("data", 'sample_640x360.mp4'))
    i_frame = 0
    while True:
        i_frame += 1
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (64, 64))
        if await me.emit(frame, DType.ND_ARR):

            if i_frame % 10 == 0:
                print(f"{i_frame}")
        else:
            print('missed frame: {}'.format(i_frame))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
