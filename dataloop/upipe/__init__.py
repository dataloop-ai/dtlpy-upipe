from .__version__ import version as __version__
from . import types
from . import node
from .entities import DataFrame, MemQueue, Processor, Process, Pipe, DType


def debugger():
    from .node import ComputeNode
    import webbrowser
    webbrowser.open(ComputeNode.debugger_url(), new=0, autoraise=True)
