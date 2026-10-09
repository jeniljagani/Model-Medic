"""
modelmedic.cli
==============
Command-line interface for ModelMedic.

Commands:
    modelmedic diagnose <task_id>        Diagnose a ClearML experiment
    modelmedic ping                      Test ClearML server connection
    modelmedic version                   Show ModelMedic version
"""
from .__main__ import main

__all__ = ["main"]
