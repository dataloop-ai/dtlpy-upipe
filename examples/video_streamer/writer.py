import asyncio
import cv2
from dataloop.upipe import Worker, DataFrame


def on_frame(frame: DataFrame):
    if frame.data is None:
        return
    cv2.imshow("result", frame.data)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return


async def main():
    print("Hello writer")
    proc = Worker("writer")
    await proc.join()
    frame_cnt = 0
    while True:
        if frame_cnt == 400:
            break
        display_frame = await proc.get_sync()
        if display_frame is None:
            break
            on_frame(display_frame)
        frame_cnt += 1
    print("Display done")
    proc.on_frame(on_frame)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
