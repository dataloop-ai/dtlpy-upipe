import asyncio
import hashlib
import string
import random

from dataloop.upipe import Worker

limit = 10000


async def main():
    global limit
    print("Hello sha processor b")
    proc = Worker("b")
    await proc.join()
    counter = 0
    while True:
        try:
            counter = await proc.get_sync()
            if counter == limit:
                break

            s = ''.join(random.choices(string.ascii_uppercase + string.digits, k=25))
            encoded = s.encode()
            for j in range(2 ** 24):
                result = hashlib.sha256(encoded)
            print(f"hash {counter} done")
        except TimeoutError:
            print("timeout")
            break
        except GeneratorExit:
            return
        if counter % 1000 == 0:
            print(f"{counter / 1000}K")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print("b Done")
