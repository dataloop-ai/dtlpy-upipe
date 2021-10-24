import asyncio
import random
import string

from mock.sdk.entities import Processor, Pipe, DType
import hashlib

limit = 10000


async def processor_a():
    global limit
    print("Hello embedded processor a")
    me = Processor("a")
    await me.connect()
    print("a connected")
    val = 1
    while True:
        if await me.emit(val, DType.U32):
            if val % 1000 == 0:
                print(f"{val / 1000}K")
            if val == limit:
                break
            val += 1
    print("a done")


async def processor_b():
    global limit
    print("Hello sha processor b")
    proc = Processor("b")
    await proc.connect()
    proc.start()
    counter = 0
    while True:
        try:
            counter = await proc.get_sync()
            if counter == limit:
                break

            s = ''.join(random.choices(string.ascii_uppercase + string.digits, k=counter**2))
            encoded = s.encode()
            for j in range(2**24):
                result = hashlib.sha256(encoded)
            print(f"hash {counter} done")
        except TimeoutError:
            print("timeout")
            break
        if counter % 1000 == 0:
            print(f"{counter / 1000}K")


async def main():
    a = Processor('a', func=processor_a)
    b = Processor('b', func=processor_b)
    pipe = Pipe('plus-one')
    pipe.add(a).add(b)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
