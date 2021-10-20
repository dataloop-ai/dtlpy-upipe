import logging
import asyncio
import sys

import mock.sdk as up
from mock.sdk import Queue

logging.basicConfig(level=logging.DEBUG, format='C:%(process)d - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    logger.info("Hello c")
    proc = up.Processor("c")
    await proc.connect()
    proc.start()
    logger.info("b started")
    first = True
    while True:
        try:
            counter = await proc.get_sync()
            # if counter + 1 != q.exe_counter:
            #     raise IndexError("Q counter mismatch ")
            if first:
                first = False
                logger.info("b got first message")
                sys.stdout.flush()
        except TimeoutError:
            logger.info("timeout")
            break
        if counter % 1000 == 0:
            logger.info(f"{float(counter / 1000)}K")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
