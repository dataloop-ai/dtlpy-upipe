import blocks.mock.sdk_ as up
import time


def on_data(data):
    print("got message{}".format(data))
    proc.emit(data+1)


if __name__ == "__main__":
    proc = up.Processor("a")
    proc.on_data(on_data)
    proc.start()
