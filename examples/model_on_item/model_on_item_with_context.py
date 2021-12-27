import numpy as np
import asyncio
from upipe import Processor, Pipe, DType


class DummyModel:
    def predict(self, image):
        return [0, 0, 0, 0, 1]


async def get_item():
    print("loading get_item")
    me = Processor("get_item")
    await me.connect()
    print("get_item connected")
    while True:
        msg = await me.get_sync(timeout=np.inf)
        item_id = msg['item_id']
        print('getting item id: {}'.format(item_id))
        bgr = np.random.randint(low=0, high=255, size=(100, 100), dtype='uint8')
        msg['image'] = bgr.tolist()
        await me.emit(msg, DType.JSON)


async def age_detection():
    print("loading age detector")
    me = Processor("age_detection")
    await me.connect()
    print("age_detection connected")
    age_detector = DummyModel()
    while True:
        msg = await me.get_sync(timeout=np.inf)
        print('age_detection GOT THE MSG')
        image = msg['image']
        predictions = age_detector.predict(image=image)
        msg['first_predictions'] = predictions
        await me.emit(msg, DType.JSON)


async def nude_net():
    print("Hello nude_net")
    me = Processor("nude_net")
    await me.connect()
    nude_net_module = DummyModel()
    while True:
        msg = await me.get_sync(timeout=np.inf)
        print('nude_net GOT THE MSG')
        image = msg['image']
        predictions = nude_net_module.predict(image=image)
        msg['second_predictions'] = predictions
        await me.emit(msg, DType.JSON)


async def main():
    a = Processor('get_item', func=get_item)
    b = Processor('age_detection', func=age_detection)
    c = Processor('nude_net', func=nude_net)
    pipe = Pipe('content-detection')
    pipe.add(a).add(b).add(c)
    await pipe.start()
    counter = 0
    while pipe.running:
        output = await pipe.emit_sync({'item_id': '42'})
        print("GOT OUTPUT:")
        print(output)
        if counter % 100 == 0 and counter > 0:
            print(f"from main: {counter / 1000}K")

        if counter > 5000 == 0:
            print(f"Done : {counter / 1000}K")
            break
    await pipe.terminate()
    await pipe.wait_for_completion()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
