"""
modelmedic.integration.dataset_fetcher
========================================
Downloads ClearML Dataset files to a local temp directory
so ModelMedic analysis modules can work on them with pandas/numpy.
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DatasetFetcher:
    """
    Downloads a ClearML Dataset to a local directory for analysis.

    Usage
    -----
        fetcher = DatasetFetcher()
        local_path = fetcher.get_local_path("dataset-id")
        # local_path is a Path to a directory with the dataset files
    """

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        self._cache_dir = cache_dir or os.path.join(
            tempfile.gettempdir(), "modelmedic_datasets"
        )
        os.makedirs(self._cache_dir, exist_ok=True)

    def get_local_path(
        self,
        dataset_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
        dataset_project: Optional[str] = None,
        writable: bool = False,
    ) -> Path:
        """
        Get a local path to the dataset files.

        Uses ClearML's built-in caching — files are only downloaded once.

        Parameters
        ----------
        dataset_id : str, optional
            ClearML Dataset ID.
        dataset_name : str, optional
            Dataset name (used if dataset_id not provided).
        dataset_project : str, optional
            Project name for the dataset lookup.
        writable : bool
            If True, returns a mutable copy of the dataset directory.

        Returns
        -------
        Path
            Local filesystem path to the dataset directory.
        """
        from .clearml_client import ClearMLClient
        client = ClearMLClient()
        dataset = client.get_dataset(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            dataset_project=dataset_project,
        )

        logger.info(
            "Downloading dataset '%s' (id=%s) to local cache...",
            getattr(dataset, "name", "unknown"),
            getattr(dataset, "id", "unknown"),
        )

        if writable:
            local_path = dataset.get_mutable_local_copy(
                target_folder=os.path.join(self._cache_dir, dataset.id + "_mutable")
            )
        else:
            local_path = dataset.get_local_copy()

        path = Path(local_path)
        logger.info("Dataset available at: %s", path)
        return path

    def get_metadata(
        self,
        dataset_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
        dataset_project: Optional[str] = None,
    ) -> dict:
        """Return dataset metadata without downloading files."""
        from .clearml_client import ClearMLClient
        client = ClearMLClient()
        dataset = client.get_dataset(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            dataset_project=dataset_project,
        )
        return {
            "id": dataset.id,
            "name": dataset.name,
            "project": dataset.project,
            "version": dataset.version,
            "tags": list(dataset.tags or []),
            "is_final": dataset.is_final(),
            "num_chunks": dataset.get_num_chunks(),
            "metadata": dataset.get_metadata() or {},
        }

    def resolve_dataset_file(
        self,
        dataset_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
        dataset_project: Optional[str] = None,
    ) -> Path:
        """
        Downloads a dataset and deterministically resolves the primary file.
        Raises an error if the selection is ambiguous (multiple valid files).
        """
        dir_path = self.get_local_path(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            dataset_project=dataset_project,
        )

        supported_exts = {".csv", ".parquet", ".pq", ".xls", ".xlsx"}
        candidate_files = []

        for root, _, files in os.walk(dir_path):
            for file in files:
                path = Path(root) / file
                if path.suffix.lower() in supported_exts:
                    candidate_files.append(path)

        if not candidate_files:
            raise FileNotFoundError(
                f"No supported dataset files found in {dir_path}. "
                f"Supported formats: {', '.join(supported_exts)}"
            )

        if len(candidate_files) > 1:
            file_list = "\n".join(f"- {f.name}" for f in candidate_files)
            raise ValueError(
                f"Ambiguous dataset contents: found multiple supported files.\n"
                f"{file_list}\n"
                "ModelMedic currently requires a single structured file per dataset."
            )

        selected_file = candidate_files[0]
        logger.info("Resolved primary dataset file: %s", selected_file.name)
        return selected_file

