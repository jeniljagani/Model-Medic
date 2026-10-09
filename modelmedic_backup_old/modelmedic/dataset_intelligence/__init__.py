"""
modelmedic.dataset_intelligence
================================
Analyzes raw datasets for quality problems before training.
"""
from .models import (
    DatasetDiagnosisReport,
    DatasetSummary,
    OverallHealthScore,
    Severity,
    MissingDataFindings,
    DuplicateFindings,
    ClassBalanceFindings,
    OutlierFindings,
    DistributionFindings,
    CorrelationFindings,
    MulticollinearityFindings,
    TargetFindings,
    LeakageFindings
)
from .analyzer import DatasetAnalyzer
from .loaders import load_dataset, DatasetLoader

__all__ = [
    "DatasetAnalyzer",
    "DatasetDiagnosisReport",
    "DatasetSummary",
    "OverallHealthScore",
    "Severity",
    "MissingDataFindings",
    "DuplicateFindings",
    "ClassBalanceFindings",
    "OutlierFindings",
    "DistributionFindings",
    "CorrelationFindings",
    "MulticollinearityFindings",
    "TargetFindings",
    "LeakageFindings",
    "load_dataset",
    "DatasetLoader"
]
