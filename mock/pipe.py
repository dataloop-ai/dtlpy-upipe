import sdk_ as up

if __name__ == "__main__":
    a = up.Processor('a', path="a.py")
    b = up.Processor('b', path="b.py")
    pipe = up.Pipe('plus-one')
    pipe.add(a).add(b)
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
