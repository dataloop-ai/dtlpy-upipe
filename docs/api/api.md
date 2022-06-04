# uPipe API

uPipe API is designed with simplicity and performance in mind.

### Processor ###
Processor contains the code to be executed in a single pipe stage, Processor execution is manifested a [Process](#process), often more than one process will exist for parallel execution.

The Processor is the basic pipeline unit, a pipe is a [tree](https://en.wikipedia.org/wiki/Tree_(data_structure)) of processors. 

####<u>Processor declaration</u>

Processor name must be unique across the system and should comply to [python variable naming rules](https://www.w3schools.com/python/gloss_python_variable_names.asp) 

    p = Processor("I_AM_AN_EMPTY_PROCESSOR")

processor - code by path

    p = Processor("inline",entry='processor_code.py')

processor - inline function processor

    async def the_code():
        process = Process("inline")
        await process.join()
        print("hello from process")

    p = Processor("inline",func=the_code)

<u>Processor settings</u>

This following allow uPipe to launch UP TO 8 processes from this processor

    p = Processor("inline",entry='processor_code.py', settings=APIProcSettings(autoscale=8))

The processor declares the memory size of its input queue, 1000 OS pages (4K bytes / page) is the default

    p = Processor("inline",entry='processor_code.py', settings=APIProcSettings(input_buffer_size=1000 * 4096))

<u>Processor configuration</u>

The processor configuration allows the processor to share initial data with its processes as dictionary


    async def the_code():
        process = Process("inline")
        await process.join()
        print(f"foo:{process.config['foo']}") #output foo:bar
    
    config = {"foo": "bar}
    p = Processor("inline",func=the_code,config=config)

####<u>Processor methods</u>
<i>add(child:Processor)</i> : Add a child processor 

<i>get_child(name:str)</i> : Get a direct child processor by name

<i>all_child_procs()</i> : Get all children (direct and none-direct) as list

####<u>Processor properties</u>

<i>count</i> : Get all children (direct and none-direct) number

<i>config_hash</i> : unique hash string of the config

<i>id</i> : the unique id of the processor

<i>executable</i> : the executable script of the processor

<i>processor_def</i> : the API entity of the processor object

###Worker
Worker is any piece of code with no specific limitation on it. anywhere in the code you can instantiate a reference to the current running process in order to :read config, receive data and emit data. the _Worker_ class allows this communication

The worker can be instantiated with the same name of its launch processor, this is explicit naming.
```python
    me = Worker("the_processor_name") 
```
by default uPipe **automatically** assigned the processes the name to launched process using the environment variable UPIPE_PROCESS_NAME

**Note:explicit naming will take priority over the environment variables**
```python    
    me = Worker() # name is taken from os.environ['UPIPE_PROCESS_NAME']
    await me.join()
```
####<u>Worker methods</u>

<i>join()</i> : Notify uPipe this worker is joining the processing pool, join must be called before any data operation 

<i>emit(data:DataFrame | data , d_type: entities.DType = None)</i> : 

* emit outputs the processor data, data type is automatically calculated by default. incase native data types are given to emit it will wrap it in dataframe, if dataframe is supplied it will be passed as is. 
* once emit is called the data is emitted to **all** connected queues. 
* last processor in the pipe emits into the pipe [sink]()
* emit returns boolean - True is success, False otherwise (usually because queue is full)


<i>emit_sync(data:DataFrame | data , d_type: entities.DType = None)</i> : 

just like emit, but waits for queue to be available. 


<i>get()</i>: receive data for processing, pull data from incoming queue.  Incase there are multiple input queues get will do [Round robin scheduling](https://en.wikipedia.org/wiki/Round-robin_scheduling) on all input queues.  

<i>get_sync()</i> : just like get, but waits for data to be available. 

<i>get_stats</i> : Get this processor performance metrics, see [Performance monitoring]() for more details 

####<u>Worker properties</u>

```properties
config_hash : unique hash string of the config

id : the unique id of the worker

executable : the executable script of the worker

process_def : the API entity of the worker object
```
###Pipe

Pipe is both processor and a worker
* The Pipe is the root Processor of the processing tree and support all processor methods. 
* The Pipe is also a Worker, what allows it to _emit_ data into the processing tree. 
* get/get_sync are not defined on the Pipe

The Pipe is instantiated with a name, that is required to be unique among all Processors.
Processors are [_chained_](https://en.wikipedia.org/wiki/Method_chaining) using the _add_ method:


    processor1 = Processor('processor1', func=processor_a)
    processor2 = Processor('processor2', func=processor_b)
    pipe1 = Pipe('pipe1')
    pipe1.add(processor1).add(processor2)

####<u>Pipe methods</u>
<i>load</i> : load the pipe before execution, load will start the [uPipe node]() if node has not been started. 

<i>start</i>: start the pipe execution, pipe is loaded if not. 

<i>wait_for_completion</i>: wait for all Processes to complete execution, will never return if pipe contains infinite processes. 

<i>terminate</i>: terminate the pipe execution, termination will allow processors to drain all existing data before shutting down. 


####<u>Pipe properties</u>


<i>id</i> : the unique id of the pipe

<i>running</i> : Boolean, indicating the pipe is currently executing

<i>completed</i> : Boolean, indicating the pipe has completed execution

<i>pending_termination</i> : Boolean, indicating the pipe is draining data towards termination

<i>pipe_def</i> : the API entity of the pipe object
