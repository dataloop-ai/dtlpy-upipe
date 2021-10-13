import mock.sdk as up
if __name__ == "__main__":
    print("Hello a")
    me = up.Processor("a")
    val = 1
    me.emit(val.to_bytes(2,'big'))
