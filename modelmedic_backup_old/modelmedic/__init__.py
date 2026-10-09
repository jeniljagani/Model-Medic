"""
ModelMedic
==========
Intelligent ML diagnosis, optimization, explainability,
and AI-assistance layer built on top of ClearML.

ModelMedic = ClearML infrastructure + ModelMedic Intelligence Layer

Usage
-----
    from modelmedic.diagnosis import DiagnosisEngine
    from modelmedic.integration import ClearMLClient

    client = ClearMLClient()
    task = client.get_experiment("your-task-id")
    engine = DiagnosisEngine(task)
    report = engine.run()
    print(report.summary())
"""
from .version import __version__

__all__ = ["__version__"]
