import mock.sdk as up

if __name__ == "__main__":
    a = up.Processor('reader')
    b = up.Processor('writer')
    pipe = up.Pipe('video-streamer')
    pipe.add(a).add(b)
    pipe.start()
    print("Running")
