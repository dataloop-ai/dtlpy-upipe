import asyncio
import logging

import numpy as np

from dataloop.upipe import Worker, DType

logging.basicConfig(level=logging.DEBUG, format='%(process)d - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("reader")


async def main():
    logger.info("Hello reader")
    me = Worker("reader")
    await me.join()
    logger.info("reader starter")

    frame = np.random.randint(0, 255, (1000, 1000), dtype='uint8')
    counter = 0
    while True:
        if await me.emit(frame, DType.ND_ARR):
            counter += 1
            if counter % 100 == 0:
                logger.info(f"{counter / 1000}K")
            if counter == 1000:
                break


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
