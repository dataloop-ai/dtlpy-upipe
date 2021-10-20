import logging
import asyncio
import numpy as np
import mock.sdk as up
from mock.sdk import Queue

logging.basicConfig(level=logging.DEBUG, format='%(process)d - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("reader")


async def main():
    logger.info("Hello reader")
    me = up.Processor("reader")
    await me.connect()
    logger.info("reader starter")

    frame = np.random.randint(0, 255, (1000, 1000), dtype='uint8')
    counter = 0
    while True:
        if await me.emit(frame, up.DType.ND_ARR):
            counter += 1
            if counter % 10000 == 0:
                logger.info(f"{counter / 1000}K")
            if counter % 100000 == 0:
                break


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
