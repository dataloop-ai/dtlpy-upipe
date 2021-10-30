import logging
import asyncio
import numpy as np
from mock.sdk.entities import Processor, Pipe, MemQueue, DType

logging.basicConfig(level=logging.DEBUG, format='%(process)d - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("reader")


async def main():
    logger.info("Hello reader")
    me = Processor("reader")
    await me.connect()
    logger.info("reader starter")

    frame = np.random.randint(0, 255, (1000, 1000), dtype='uint8')
    counter = 0
    while True:
        if await me.emit(frame, DType.ND_ARR):
            counter += 1
            if counter % 1000 == 0:
                logger.info(f"{counter / 1000}K")
            if counter == 3000:
                break


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
