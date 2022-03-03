from .entities import *
from .__version__ import version as __version__


def debugger():
    from .node import ComputeNode
    import webbrowser
    webbrowser.open(ComputeNode.debugger_url(), new=0, autoraise=True)
