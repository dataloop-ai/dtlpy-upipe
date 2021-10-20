import logging
import asyncio

import mock.sdk as up
from mock.sdk import Queue

logging.basicConfig(level=logging.DEBUG, format='%(process)d - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    logger.info("Hello a")
    me = up.Processor("a")
    await me.connect()
    logger.info("a starter")
    val = 0
    q: Queue = me.get_next_q_to_emit()
    while True:
        if await me.emit(val, up.DType.U32):
            val += 1
            if val % 10000 == 0:
                logger.info(f"{val / 1000}K")
                logger.info(q.status_str)
            if val % 100000 == 0:
                break


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
