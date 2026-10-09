"""
modelmedic.diagnosis
====================
Model diagnosis: detects overfitting, underfitting, training instability,
and metric problems from ClearML experiment data.
"""
from .engine import DiagnosisEngine, DiagnosisReport
from .overfitting import OverfittingDetector
from .underfitting import UnderfittingDetector
from .metric_analysis import MetricAnalyzer
from .training_stability import TrainingStabilityAnalyzer

__all__ = [
    "DiagnosisEngine",
    "DiagnosisReport",
    "OverfittingDetector",
    "UnderfittingDetector",
    "MetricAnalyzer",
    "TrainingStabilityAnalyzer",
]
