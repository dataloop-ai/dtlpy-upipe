import asyncio

from dataloop.upipe import Worker


async def main():
    print("Hello b")
    proc = Worker("b")
    await proc.join()
    counter = 0
    while True:
        try:
            counter = await proc.get_sync()
            if counter == 15000:
                break
        except TimeoutError:
            print("timeout")
            break
        if counter % 1000 == 0:
            print(f"{counter / 1000}K")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print("b Done")
