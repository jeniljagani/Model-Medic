"""
modelmedic.integration.clearml_client
======================================
Single bridge point to the ClearML SDK.

All ClearML imports in ModelMedic are centralized here.
"""
from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ClearMLClient:
    """
    ModelMedic's gateway to ClearML.

    Wraps the ClearML Python SDK so the rest of ModelMedic never
    imports from clearml directly. This makes it trivial to update
    or mock ClearML in tests.

    Usage
    -----
        client = ClearMLClient()
        task = client.get_experiment("task-id-here")
        projects = client.list_projects()
    """

    def __init__(self) -> None:
        # Import ClearML lazily so ModelMedic can run in offline/test mode
        # without requiring a live ClearML connection at import time.
        try:
            from clearml import Task, Dataset, Model  # noqa: F401
            from clearml.backend_api.session.client import APIClient  # noqa: F401
            self._available = True
        except ImportError:
            self._available = False
            logger.warning(
                "ClearML SDK not found. Install it with: pip install clearml"
            )

    def _require_clearml(self) -> None:
        if not self._available:
            raise RuntimeError(
                "ClearML SDK is required but not installed. "
                "Run: pip install clearml"
            )

    # ── Experiments (Tasks) ──────────────────────────────────────────────────

    def get_experiment(self, task_id: str):
        """Return a ClearML Task object by ID."""
        self._require_clearml()
        from clearml import Task
        return Task.get_task(task_id=task_id)

    def get_experiments(
        self,
        project_name: Optional[str] = None,
        task_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        max_results: int = 50,
    ) -> list:
        """Return a list of ClearML Task objects matching the given filters."""
        self._require_clearml()
        from clearml import Task
        from typing import Any
        filters: dict[str, Any] = {}
        if project_name:
            filters["project_name"] = project_name
        if task_name:
            filters["task_name"] = task_name
        if tags:
            filters["tags"] = tags
        if status:
            filters["status"] = [status]
        return Task.get_tasks(**filters)[:max_results]

    def get_latest_experiment(self, project_name: str) -> Optional[object]:
        """Return the most recently updated task in a project."""
        tasks = self.get_experiments(project_name=project_name, max_results=1)
        return tasks[0] if tasks else None

    # ── Datasets ────────────────────────────────────────────────────────────

    def get_dataset(self, dataset_id: Optional[str] = None,
                    dataset_name: Optional[str] = None,
                    dataset_project: Optional[str] = None):
        """Return a ClearML Dataset object."""
        self._require_clearml()
        from clearml import Dataset
        if dataset_id:
            return Dataset.get(dataset_id=dataset_id)
        return Dataset.get(
            dataset_name=dataset_name,
            dataset_project=dataset_project,
        )

    def list_datasets(self, project: Optional[str] = None) -> list:
        """List all datasets, optionally filtered by project."""
        self._require_clearml()
        from clearml import Dataset
        return Dataset.list_datasets(dataset_project=project) or []

    # ── Models ───────────────────────────────────────────────────────────────

    def get_model(self, model_id: str):
        """Return a ClearML Model object by ID."""
        self._require_clearml()
        from clearml import Model
        return Model(model_id=model_id)

    # ── Projects ─────────────────────────────────────────────────────────────

    def list_projects(self) -> list:
        """Return all project names available in the workspace."""
        self._require_clearml()
        from clearml import Task
        return Task.get_projects()

    # ── Health check ─────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Return True if ClearML server is reachable."""
        self._require_clearml()
        try:
            from clearml.backend_api.session.client import APIClient
            client = APIClient()
            client.projects.get_all(name="*")
            return True
        except Exception as exc:
            logger.warning("ClearML ping failed: %s", exc)
            return False
