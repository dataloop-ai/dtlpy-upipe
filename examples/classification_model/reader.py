import torchvision.datasets
import asyncio
from dataloop.upipe import Worker, Processor, DType
import numpy as np
import logging
import time

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d,%H:%M:%S')
logger = logging.getLogger("reader")
limit = 100000

testset = torchvision.datasets.CIFAR10(root='./data',
                                       train=False,
                                       download=True,
                                       transform=None)


async def main():
    global limit
    logger.info("Hello stressor reader")
    me = Worker("reader")
    await me.join()
    logger.info("reader connected")
    pass_counter = 0
    failed_counter = 0
    tic = time.time() - 1e-6
    while True:
        pil_image, label = testset[np.random.randint(0, len(testset))]
        # pil_image, label = testset[0]
        image = np.asarray(pil_image)
        # logger.info(f'reading label {label}')
        if await me.emit_sync(image, DType.ND_ARR):
            pass_counter += 1
            # logger.info(f'emitted {label}')

        else:
            failed_counter += 1
            # logger.info(f"failed emitting")
            ...
        counter = pass_counter + failed_counter
        # if counter % 1000 == 0:
        #     logger.info(
        #         f"counter: {counter / 1000}K, PASS FPS: {pass_counter / (time.time() - tic)}, FAILED FPS: {failed_counter / (time.time() - tic)}")
        # if counter == limit:
        #     break
        counter += 1
    logger.info("reader done")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    logger.info(" a Done")
