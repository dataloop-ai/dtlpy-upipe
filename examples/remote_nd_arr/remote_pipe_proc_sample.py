import asyncio
import upipe.types
from upipe import Processor, Pipe


async def main():
    print("Hello pipe")
    reader = Processor('reader', entry='reader.py')
    writer = Processor('writer', entry='writer.py', settings=upipe.types.APIProcSettings(host="localhost"))
    pipe = Pipe('streamer')
    pipe.add(reader).add(writer)
    await pipe.start()
    print("Running")
    await pipe.wait_for_completion()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

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
