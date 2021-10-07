import blocks.mock.sdk_ as up


if __name__ == "__main__":
    a = up.Block(name='a')
    b = up.Block(name='b')

    pipe = up.Pipe(name='plus-one')

    pipe.add(a)
    pipe.add(b)

    pipe.start()

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
