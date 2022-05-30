# uPipe #

Micro-pipe is asyncio based framework for running **simple**,high performance, parallel and synchronized python
processes within a single machine.  
uPipe comes with auto-scaler for maximum throughput and hardware utilization and a monitoring tool.

```python
a = Processor('a', entry='./a.py', config=config)
b = Processor('b', entry='./b.py', config=config)
pipe = Pipe('plus-one')
pipe.add(a).add(b)
await pipe.start()
await pipe.wait_for_completion()
print("Running")
```

## Why uPipe ? ##

In the world of machine learning python has taken the stage as the go-to programming language, yet python has few
fundamental issues preventing it from being production friendly

### Parallel processing ###

Python has a built-in weakness for parallel data processing, this weakness is sourced in the core of python at
the [GIL](https://wiki.python.org/moin/GlobalInterpreterLock)

The GlobalInterpreterLock prevents from different threads to access memory (and therefore variables) in parallel. This
essentially means that a multi-threaded python program executes slower compared to single thread on CPU intensive
workloads. Python also offers multiprocessing capabilities that are not blocked by GIL since the workloads are running
in different processes, yet using multiprocessor does not allow sharing memory and communication between process
implicitly uses [Pickling](https://docs.python.org/3/library/pickle.html) for data sharing, which in turn significantly
degrades data throughput.

### Parallel optimization ###

Any given processing workload is bounded by critical hardware resources where the leading resources are I/O (Network and
disk), Memory and CPU. Machine learning also introduces additional resources like GPU cores, CPU memory and other AI
specific accelerators. Optimizing the overall data on a given machine is a process of trial and error, often includes
non-trivial technical challenges.uPipe implements [AutoScaling](https://en.wikipedia.org/wiki/Autoscaling) by process
into the single machine with maximum pipeline throughput as goal.

### Simple ###

uPipe exposes a simple API for creating data pipelines from existing packages and library's run with fews line of code.

The basics entities:

* DataFrame: Arbitrary binary data that is shared between processors.
* Processor: A python code that can receive, process and generate(emit) data frames. Processor is a logical entities
  that can encapsulate many (os) processes of the same processor code.
* Pipe: The Pipeline the defines the data flow between Processors and manages the processing execution.

### Read more ###

* [uPipe basics](docs/basics/basics.md)
* [uPipe API](docs/api/api.md)
* uPipe architecture
* uPipe design

### Install ###

```shell
pip install dataloop-upipe
```

### Import ###

    from dataloop.upipe import Processor, Pipe

## Usage ##

### Processor declaration ###

Processor can be defined inline methods(_func_) or as external scripts (_entry_) in order to be used in pipeline
definition, the name for each processor must be a unique string and used to identify the processor.

```python
a = Processor('my name is A', func=processor_a)
b = Processor('b', entry='./b.py')
```

### Pipe definition ###

Processor can be chained to pipe and to each other by the _add_ method
```python
pipe = Pipe('some-pipe') 
pipe.add(a).add(b) #a,b are processors 
```

### Joining a Processor to a pipe###

This code is declaring the Processors code and _join_ in order to be able to receive and emit data frames.

```python
proc = Processor("b")
await proc.join()
# Processor is now ready to ingest and emit data 
```
### Acquiring data by processor ###

Processor can get data using the _get_  and _get_sync_ methods
```python
proc = Processor("b")
await proc.join()
# Processor is now ready to ingest and emit data 
#get data frame, return None if no data available 
data_frame = await proc.get()
#get data frame, wait until data available 
data_frame = await proc.get_sync()
```
### Emitting data by processor ###

Processor can emit data frame for the next Processor in Pipe using the _emit_  and _emit_sync_ methods
```python
proc = Processor("b")
await proc.join()
# Processor is now ready to ingest and emit data 
#emit data frame, return None if no space (back pressure from next processor) 
await proc.emit()
#emit data frame, wait if no space (back pressure) 
await proc.emit_sync()
```
### start pipe ###
```python
await pipe.start()
await pipe.wait_for_completion()
```
### terminate pipe ###
```python
await pipe.terminate()
await pipe.wait_for_completion() # wait for existing data to complete
```