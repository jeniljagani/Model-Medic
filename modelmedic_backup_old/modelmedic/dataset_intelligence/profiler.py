"""
modelmedic.dataset_intelligence.profiler
=========================================
Profiles datasets to compute base statistics and properties.
"""
from __future__ import annotations

import logging
from typing import Dict, Any

import pandas as pd

from .models import DatasetSummary

logger = logging.getLogger(__name__)


class DatasetProfiler:
    """Profiles a dataset to extract structural and memory characteristics."""
    
    def __init__(self) -> None:
        pass

    def profile_summary(self, df: pd.DataFrame) -> DatasetSummary:
        """Computes the overall dataset summary."""
        rows, cols = df.shape
        
        # memory_usage(deep=True) is accurate for objects/strings but can be slow on huge datasets.
        # We will use deep=False for speed on huge datasets, but deep=True is safer.
        # Let's conditionally use deep=True for datasets < 1M cells.
        total_cells = rows * cols
        use_deep = total_cells < 1_000_000
        mem_bytes = df.memory_usage(deep=use_deep).sum()
        mem_mb = float(mem_bytes) / (1024 * 1024)

        dtypes_summary = {
            "numeric": int(df.select_dtypes(include="number").shape[1]),
            "categorical": int(df.select_dtypes(include=["object", "category"]).shape[1]),
            "datetime": int(df.select_dtypes(include=["datetime"]).shape[1]),
            "boolean": int(df.select_dtypes(include=["bool"]).shape[1]),
        }

        return DatasetSummary(
            rows=rows,
            columns=cols,
            memory_usage_mb=mem_mb,
            dtypes_summary=dtypes_summary,
        )
