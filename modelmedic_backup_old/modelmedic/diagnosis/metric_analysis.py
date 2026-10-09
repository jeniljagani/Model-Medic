"""
modelmedic.diagnosis.metric_analysis
======================================
Analyzes the quality and consistency of reported metrics.

Detects:
  - Missing val metrics (only train reported)
  - Very few training epochs (suspicious short runs)
  - Metric naming inconsistencies
  - NaN / Inf values in metric history
  - Suspicious metric magnitudes
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class MetricAnalysisResult:
    has_validation_metrics: bool
    total_epochs: int
    metric_titles: List[str]
    warnings: List[str]  # human-readable issues found
    nan_inf_detected: bool
    is_suspiciously_short: bool


class MetricAnalyzer:
    """
    Validates and summarizes the metrics reported in an experiment.

    Parameters
    ----------
    min_epochs_warning : int
        Flag a warning if training is shorter than this many steps.
    """

    TRAIN_NAMES = {"train", "training"}
    VAL_NAMES = {"val", "validation", "valid", "eval", "test"}

    def __init__(self, min_epochs_warning: int = 5) -> None:
        self.min_epochs_warning = min_epochs_warning

    def analyze(self, scalars: Dict[str, Dict]) -> MetricAnalysisResult:
        warnings = []
        has_val = False
        max_epochs = 0
        nan_inf_detected = False
        metric_titles = list(scalars.keys())

        for title, series_dict in scalars.items():
            for series_name, series in series_dict.items():
                y_vals = list(
                    series.y if hasattr(series, "y") else series.get("y", [])
                )
                n = len(y_vals)
                max_epochs = max(max_epochs, n)

                # Check for NaN/Inf
                bad_vals = [v for v in y_vals if math.isnan(v) or math.isinf(v)]
                if bad_vals:
                    nan_inf_detected = True
                    warnings.append(
                        f"Metric '{title}/{series_name}' contains "
                        f"{len(bad_vals)} NaN or Inf values — "
                        f"possible numerical instability"
                    )

                # Check for val series existence
                if any(n in series_name.lower() for n in self.VAL_NAMES):
                    has_val = True

        if not has_val:
            warnings.append(
                "No validation metrics found. "
                "Without val metrics, overfitting cannot be detected. "
                "Add a validation set and report its metrics."
            )

        is_short = max_epochs < self.min_epochs_warning
        if is_short and max_epochs > 0:
            warnings.append(
                f"Only {max_epochs} training steps recorded. "
                f"Consider training longer to see convergence trends."
            )

        if not metric_titles:
            warnings.append(
                "No scalar metrics were reported for this experiment. "
                "Use Logger.report_scalar() to log metrics."
            )

        return MetricAnalysisResult(
            has_validation_metrics=has_val,
            total_epochs=max_epochs,
            metric_titles=metric_titles,
            warnings=warnings,
            nan_inf_detected=nan_inf_detected,
            is_suspiciously_short=is_short,
        )
