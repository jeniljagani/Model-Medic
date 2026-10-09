"""
modelmedic.dataset_intelligence.loaders
========================================
Flexible dataset loaders supporting various file formats.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)


class DatasetLoader(ABC):
    """Abstract base class for dataset loaders."""
    @abstractmethod
    def load(self, filepath: str | Path) -> pd.DataFrame:
        pass


class CSVLoader(DatasetLoader):
    """Loads datasets from CSV files."""
    def load(self, filepath: str | Path) -> pd.DataFrame:
        logger.info("Loading CSV dataset from %s", filepath)
        return pd.read_csv(filepath)


class ParquetLoader(DatasetLoader):
    """Loads datasets from Parquet files."""
    def load(self, filepath: str | Path) -> pd.DataFrame:
        logger.info("Loading Parquet dataset from %s", filepath)
        return pd.read_parquet(filepath)


class ExcelLoader(DatasetLoader):
    """Loads datasets from Excel files."""
    def load(self, filepath: str | Path) -> pd.DataFrame:
        logger.info("Loading Excel dataset from %s", filepath)
        # Attempt to load the first sheet
        return pd.read_excel(filepath)


def get_loader(filepath: str | Path) -> DatasetLoader:
    """
    Returns an appropriate loader for the given filepath.
    Raises ValueError if the format is unsupported.
    """
    path = Path(filepath)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return CSVLoader()
    elif suffix in (".parquet", ".pq"):
        return ParquetLoader()
    elif suffix in (".xls", ".xlsx"):
        return ExcelLoader()
    
    raise ValueError(f"Unsupported dataset format: {suffix}")


def load_dataset(filepath: str | Path) -> pd.DataFrame:
    """
    Convenience function to load a dataset from a file deterministically.
    """
    loader = get_loader(filepath)
    return loader.load(filepath)
