import asyncio
from mock.sdk.entities import Queue, Processor


async def main():
    print("Hello c")
    proc = Processor("c")
    await proc.connect()
    counter = 0
    proc.start()
    while True:
        try:
            value = await proc.get_sync()
            counter += 1
            if counter == 200000:
                break
        except TimeoutError:
            print("timeout")
            break
        if counter % 10000 == 0:
            print(f"{counter / 1000}K = {value}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print("c Done")
