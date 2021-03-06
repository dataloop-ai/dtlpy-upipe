import asyncio
import logging
import sys
import time

from dataloop.upipe import Worker

logging.basicConfig(level=logging.DEBUG, format='%(process)d - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("writer")


async def main():
    logger.info("Hello writer")
    proc = Worker("writer")
    await proc.join()
    logger.info("writer started")
    first = True
    counter = 0
    tic = time.time()
    while True:
        counter += 1
        if counter == 1000:
            break
        try:
            frame = await proc.get_sync()
            if first:
                first = False
                logger.info("writer got first message")
                sys.stdout.flush()
        except TimeoutError:
            logger.info("timeout")
            break
        if counter % 100 == 0:
            logger.info(f"got shape {frame.shape}, rate: {counter / (time.time() - tic)}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
