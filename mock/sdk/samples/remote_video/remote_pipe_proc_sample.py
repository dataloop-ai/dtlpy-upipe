import asyncio

import mock.sdk as up


async def main():
    print("Hello pipe")
    reader = up.Processor('reader', path='reader.py')
    writer = up.Processor('writer', path='writer.py', host='localhost')
    pipe = up.Pipe('streamer')
    pipe.add(reader).add(writer)
    await pipe.start()
    print("Running")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()

    ##########################################
    #
    #
    #
    # model1 = up.Processor()
    #
    #
    # stage = pipe.add_stage(up.Stage(processors=[model1]))
    # pipe.start()
    #
    #
    #
    #
    #
