import asyncio

import mock.sdk as up


async def main():
    a = up.Processor('reader')
    b = up.Processor('writer')
    pipe = up.Pipe('video-streamer')
    pipe.add(a).add(b)
    await pipe.start()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
