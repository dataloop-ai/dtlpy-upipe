import mock.sdk as up
import time


def on_data(data):
    print("got message{}".format(data))
    #proc.emit(data+1)


if __name__ == "__main__":
    print("Hello b")
    proc = up.Processor("b")
    proc.on_data(on_data)
    proc.start()
