import mock.sdk as up

if __name__ == "__main__":
    a = up.Processor('a')
    b = up.Processor('b')
    pipe = up.Pipe('plus-one')
    pipe.add(a).add(b)
    pipe.start()
    print("Running")

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
