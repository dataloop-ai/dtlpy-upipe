import torch
import torchvision.models as models
import asyncio
import logging
import cv2
import time

from dataloop.upipe import Process

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d,%H:%M:%S')

logger = logging.getLogger("classifier")

limit = 100000

inception = models.inception_v3(pretrained=True, transform_input=True)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
logger.info(f'device is {device}')
inception.to(device)
inception.eval()


async def main():
    logger.info("Hello classifier processor")
    proc = Process("classifier")
    await proc.join()
    counter = 0
    tic = time.time()
    while True:
        try:
            image = await proc.get_sync()
            if counter == limit:
                break
            norm_image = cv2.resize(image, (256, 256)).transpose((2, 0, 1)) / 255
            pred = inception(torch.from_numpy(norm_image).unsqueeze(0).to(device).float())
            # logger.info(f"prediction is {np.argmax(pred.cpu().detach().numpy())}")
        except TimeoutError:
            logger.info("timeout")
            break
        except GeneratorExit:
            return
        if counter % 1000 == 0:
            logger.info(f"counter: {counter / 1000}K, FPS: {counter / (time.time() - tic)}")
        counter += 1


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print("classifier Done")
