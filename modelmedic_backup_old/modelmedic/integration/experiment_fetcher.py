"""
modelmedic.integration.experiment_fetcher
==========================================
Fetches all analysis-relevant data from a ClearML experiment (Task).

Returns a structured ExperimentData dataclass so the rest of ModelMedic
never has to think about ClearML API shapes.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScalarSeries:
    """One metric series — e.g. 'accuracy / train'."""
    title: str       # e.g. "accuracy"
    series: str      # e.g. "train"
    x: List[float]   # iteration / epoch values
    y: List[float]   # metric values


@dataclass
class ExperimentData:
    """
    All data ModelMedic needs from one ClearML experiment.

    This is the single structured object that all ModelMedic modules
    receive and analyse. It is fully decoupled from ClearML — no ClearML
    objects leak past this boundary.
    """
    # Identity
    task_id: str
    task_name: str
    project_name: str
    task_type: str
    status: str
    created: Optional[str] = None
    started: Optional[str] = None
    completed: Optional[str] = None

    # Hyperparameters — flat dict {"section/name": value}
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Metrics — {title: {series: ScalarSeries}}
    scalars: Dict[str, Dict[str, ScalarSeries]] = field(default_factory=dict)

    # Last scalar values — {title: {series: float}}
    last_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Artifacts — {name: {"url": str, "size": int, "type": str}}
    artifacts: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Console output (last N lines)
    console_output: List[str] = field(default_factory=list)

    # Tags
    tags: List[str] = field(default_factory=list)

    # Parent task ID (for cloned/continuation experiments)
    parent_id: Optional[str] = None

    # ClearML web URL
    web_url: Optional[str] = None


class ExperimentFetcher:
    """
    Fetches all ModelMedic-relevant data from a ClearML Task.

    Usage
    -----
        fetcher = ExperimentFetcher()
        data = fetcher.fetch("task-id-here")
        # data is an ExperimentData — no ClearML objects inside
    """

    def __init__(self) -> None:
        from .clearml_client import ClearMLClient
        self._client = ClearMLClient()

    def fetch(self, task_id: str) -> ExperimentData:
        """Fetch all data for a task and return a clean ExperimentData."""
        logger.info("Fetching experiment data for task: %s", task_id)
        task = self._client.get_experiment(task_id)
        return self._extract(task)

    def fetch_multiple(self, task_ids: List[str]) -> List[ExperimentData]:
        """Fetch data for multiple tasks."""
        results = []
        for tid in task_ids:
            try:
                results.append(self.fetch(tid))
            except Exception as exc:
                logger.warning("Failed to fetch task %s: %s", tid, exc)
        return results

    def _extract(self, task) -> ExperimentData:
        """Extract clean data from a ClearML Task object."""

        # ── Scalars ──────────────────────────────────────────────────────────
        scalars: Dict[str, Dict[str, ScalarSeries]] = {}
        try:
            raw_scalars = task.get_reported_scalars()
            for title, series_dict in (raw_scalars or {}).items():
                scalars[title] = {}
                for series_name, data in series_dict.items():
                    x = list(data.get("x", []))
                    y = list(data.get("y", []))
                    scalars[title][series_name] = ScalarSeries(
                        title=title,
                        series=series_name,
                        x=x,
                        y=y,
                    )
        except Exception as exc:
            logger.warning("Could not fetch scalars for %s: %s", task.id, exc)

        # ── Last metrics ─────────────────────────────────────────────────────
        last_metrics: Dict[str, Dict[str, float]] = {}
        try:
            raw_last = task.get_last_scalar_metrics() or {}
            for title, series_dict in raw_last.items():
                last_metrics[title] = {}
                for series_name, info in series_dict.items():
                    last_metrics[title][series_name] = float(
                        info.get("value", 0.0)
                    )
        except Exception as exc:
            logger.warning("Could not fetch last metrics for %s: %s", task.id, exc)

        # ── Parameters ───────────────────────────────────────────────────────
        parameters: Dict[str, Any] = {}
        try:
            parameters = task.get_parameters_as_dict() or {}
        except Exception as exc:
            logger.warning("Could not fetch parameters for %s: %s", task.id, exc)

        # ── Artifacts ────────────────────────────────────────────────────────
        artifacts: Dict[str, Dict[str, Any]] = {}
        try:
            for name, artifact in (task.artifacts or {}).items():
                artifacts[name] = {
                    "url": getattr(artifact, "url", None),
                    "type": getattr(artifact, "type", None),
                    "size": getattr(artifact, "size", None),
                    "timestamp": str(getattr(artifact, "timestamp", "")),
                }
        except Exception as exc:
            logger.warning("Could not fetch artifacts for %s: %s", task.id, exc)

        # ── Console output ────────────────────────────────────────────────────
        console_output: List[str] = []
        try:
            raw_console = task.get_reported_console_output(number_of_reports=50)
            if raw_console:
                console_output = raw_console[-200:]  # last 200 lines
        except Exception as exc:
            logger.debug("Could not fetch console for %s: %s", task.id, exc)

        # ── Build ExperimentData ──────────────────────────────────────────────
        data_obj = task.data
        return ExperimentData(
            task_id=task.id,
            task_name=task.name,
            project_name=task.get_project_name() or "",
            task_type=str(task.task_type) if task.task_type else "",
            status=str(task.status) if task.status else "",
            created=str(getattr(data_obj, "created", "") or ""),
            started=str(getattr(data_obj, "started", "") or ""),
            completed=str(getattr(data_obj, "completed", "") or ""),
            parameters=parameters,
            scalars=scalars,
            last_metrics=last_metrics,
            artifacts=artifacts,
            console_output=console_output,
            tags=list(task.get_tags() or []),
            parent_id=getattr(data_obj, "parent", None),
            web_url=task.get_output_log_web_page(),
        )
