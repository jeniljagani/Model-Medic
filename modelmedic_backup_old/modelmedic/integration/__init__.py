"""
modelmedic.integration
======================
ClearML bridge layer.

All ModelMedic access to ClearML goes through this package.
Nothing else in ModelMedic should import from clearml directly —
use these wrappers instead. This isolates API changes to one place.
"""
from .clearml_client import ClearMLClient
from .experiment_fetcher import ExperimentData, ExperimentFetcher
from .dataset_fetcher import DatasetFetcher

__all__ = [
    "ClearMLClient",
    "ExperimentData",
    "ExperimentFetcher",
    "DatasetFetcher",
]
