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

    q: Queue = me.get_next_q_to_emit()

    frame = np.random.randint(0, 255, (256, 256), dtype='uint8')
    counter = 0
    while True:
        if await me.emit(frame, up.DType.ND_ARR):
            counter += 1
            if counter % 10000 == 0:
                logger.info(f"{counter / 1000}K")
                logger.info(q.status_str)
            if counter % 100000 == 0:
                break


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
