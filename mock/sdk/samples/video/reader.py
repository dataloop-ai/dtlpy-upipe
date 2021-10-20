import asyncio

import mock.sdk as up
import cv2

def main_sync():
    import numpy as np

    # Create a VideoCapture object and read from input file
    # If the input is the camera, pass 0 instead of the video file name
    cap = cv2.VideoCapture('sample_640x360.mp4')
    reader = up.Processor("reader.py")
    reader.connect()
    print("reader connected")
    # Check if camera opened successfully
    if not cap.isOpened():
        print("Error opening video stream or file")

    frame_cnt = 0
    # Read until video is completed
    while cap.isOpened():
        # Capture frame-by-frame
        ret, frame = cap.read()

        if ret:

            # Display the resulting frame
            cv2.imshow('Frame', frame)

            # Press Q on keyboard to  exit
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
            #await reader.emit_sync(frame)
            print(f"Sent frame {frame_cnt}")
            frame_cnt += 1

        # Break the loop
        else:
            break

    # When everything done, release the video capture object
    cap.release()

async def main():
    import numpy as np

    # Create a VideoCapture object and read from input file
    # If the input is the camera, pass 0 instead of the video file name
    cap = cv2.VideoCapture('sample_640x360.mp4')
    reader = up.Processor("reader.py")
    reader.connect()
    print("reader connected")
    # Check if camera opened successfully
    if not cap.isOpened():
        print("Error opening video stream or file")

    frame_cnt = 0
    # Read until video is completed
    while cap.isOpened():
        # Capture frame-by-frame
        ret, frame = cap.read()

        if ret:

            # Display the resulting frame
            # cv2.imshow('Frame', frame)

            # Press Q on keyboard to  exit
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
            await reader.emit_sync(frame)
            print(f"Sent frame {frame_cnt}")
            frame_cnt += 1

        # Break the loop
        else:
            break

    # When everything done, release the video capture object
    cap.release()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()