import asyncio

import dataloop.upipe as up


async def main():
    a = up.Processor('reader', entry='reader.py')
    b = up.Processor('display', entry='writer.py')
    pipe = up.Pipe('video-streamer')
    pipe.add(a).add(b)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
