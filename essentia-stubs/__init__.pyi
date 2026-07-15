"""
Type stubs for the essentia top-level package.
"""

from typing import Any, Tuple
from essentia._essentia import Algorithm, StreamingAlgorithm, reset
from essentia.common import Pool

class EssentiaError(Exception):
    error: str
    filename: str | None
    def __init__(self, error, filename=None) -> None: ...

class DebuggingModule:
    EAlgorithm: int = 1
    EConnectors: int = 2
    EFactory: int = 4
    ENetwork: int = 8
    EGraph: int = 16
    EExecution: int = 32
    EMemory: int = 64
    EScheduler: int = 128
    EPython: int = 1048576
    EPyBindings: int = 2097152

def reset() -> None: ...
