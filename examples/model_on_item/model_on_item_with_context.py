import numpy as np
import dtlpy as dl
import asyncio
import time
import cv2
from multiprocessing import Process
from upipe import Processor, Pipe, DType


class DummyModel:
    def predict(self, image):
        return [0, 0, 0, 0, 1]


async def on_item():
    print("loading init")
    me = Processor("on_item")
    await me.connect()
    print("on_item connected")
    while True:
        msg = await me.get_sync(timeout=np.inf)
        item_id: dl.Item = msg['item_id']
        print('got item id: {}'.format(item_id))
        item = dl.items.get(item_id=item_id)
        buffer = item.download(save_locally=False)
        bgr = cv2.imdecode(np.frombuffer(buffer.read(), np.uint8), -1)
        msg['image'] = bgr
        await me.emit(msg, DType.JSON)


async def age_detection():
    print("loading age detector")
    me = Processor("age_detection")
    await me.connect()
    print("age_detection connected")
    age_detector = DummyModel()
    while True:
        msg = await me.get_sync(timeout=np.inf)
        image = msg['image']
        predictions = age_detector.predict(image=image)
        msg['first_predictions'] = predictions
        await me.emit(msg, DType.JSON)


async def nude_net():
    print("Hello nude_net")
    me = Processor("nude_net")
    await me.connect()
    me.start()
    nude_net_module = DummyModel()
    while True:
        msg = await me.get_sync(timeout=np.inf)
        image = msg['image']
        predictions = nude_net_module.predict(image=image)
        msg['second_predictions'] = predictions
        await me.emit(msg, DType.JSON)


async def main():
    a = Processor('on_item', func=on_item)
    b = Processor('age_detection', func=age_detection)
    c = Processor('nude_net', func=nude_net)
    pipe = Pipe('content-detection')
    pipe.add(a).add(b).add(c)
    await pipe.start()
    await pipe.wait_for_completion()
    print("Running")


def to_run():
    loop = asyncio.get_event_loop()

    n = 20
    for i in range(n):
        print('------------ PREPARE TO RUN IN {}[s]:'.format(n - i))
        time.sleep(1)
    print('calling the pipe:')
    pipe = Pipe('content-detection')
    future = asyncio.run(pipe.emit(data={'item_id': '617fd6f591e01807b4adef92'},
                                   d_type=DType.JSON
                                   ))


def start_pipe():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    p = Process(target=to_run)
    p.start()
    p = Process(target=start_pipe)
    p.start()
    p.join()
