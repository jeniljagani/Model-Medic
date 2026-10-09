"""
modelmedic.diagnosis.overfitting
=================================
Detects overfitting from train/validation metric curves.

Overfitting = model memorizes training data, fails to generalize.
Signals:
  - Train loss continuously decreasing while val loss increases
  - Large gap between train accuracy and val accuracy
  - Val metric peaks early then degrades (divergence point)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class OverfittingResult:
    detected: bool
    severity: str          # "none" | "mild" | "moderate" | "severe"
    confidence: float      # 0.0 – 1.0
    train_val_gap: Optional[float]   # final train - val metric difference
    divergence_epoch: Optional[int]  # epoch where val started degrading
    evidence: List[str]              # human-readable evidence strings
    metric_used: Optional[str]       # which metric triggered the detection


class OverfittingDetector:
    """
    Detects overfitting from scalar metric history.

    Expects scalar series keyed by title (e.g. "loss", "accuracy")
    and series (e.g. "train", "validation", "val", "test").

    Parameters
    ----------
    gap_threshold_mild : float
        Min train-val gap (fraction) to flag mild overfitting.
    gap_threshold_severe : float
        Gap to flag severe overfitting.
    divergence_window : int
        Number of trailing epochs to check for val metric degradation.
    """

    # Common names for training series
    TRAIN_NAMES = {"train", "training", "train_loss", "train_acc"}
    # Common names for validation series
    VAL_NAMES = {"val", "validation", "valid", "eval", "test",
                 "val_loss", "val_acc", "validation_loss", "validation_accuracy"}

    def __init__(
        self,
        gap_threshold_mild: float = 0.05,
        gap_threshold_severe: float = 0.15,
        divergence_window: int = 5,
    ) -> None:
        self.gap_threshold_mild = gap_threshold_mild
        self.gap_threshold_severe = gap_threshold_severe
        self.divergence_window = divergence_window

    def analyze(self, scalars: Dict[str, Dict]) -> OverfittingResult:
        """
        Run overfitting analysis on a scalars dict.

        Parameters
        ----------
        scalars : dict
            {title: {series_name: ScalarSeries}} from ExperimentData.

        Returns
        -------
        OverfittingResult
        """
        evidence = []
        max_severity = "none"
        max_confidence = 0.0
        metric_used = None
        train_val_gap = None
        divergence_epoch = None

        # Try loss first (most reliable), then accuracy-like metrics
        priority_metrics = self._get_priority_metrics(scalars)

        for title in priority_metrics:
            series_dict = scalars.get(title, {})
            train_series = self._find_series(series_dict, self.TRAIN_NAMES)
            val_series = self._find_series(series_dict, self.VAL_NAMES)

            if train_series is None or val_series is None:
                continue

            train_y = train_series.y if hasattr(train_series, "y") else train_series.get("y", [])
            val_y = val_series.y if hasattr(val_series, "y") else val_series.get("y", [])

            if len(train_y) < 3 or len(val_y) < 3:
                continue

            is_loss = "loss" in title.lower()
            result = self._check_metric(
                title=title,
                train_y=list(train_y),
                val_y=list(val_y),
                is_loss=is_loss,
            )

            if result["confidence"] > max_confidence:
                max_confidence = result["confidence"]
                max_severity = result["severity"]
                train_val_gap = result["gap"]
                divergence_epoch = result["divergence_epoch"]
                metric_used = title
                evidence = result["evidence"]

        return OverfittingResult(
            detected=max_severity != "none",
            severity=max_severity,
            confidence=max_confidence,
            train_val_gap=train_val_gap,
            divergence_epoch=divergence_epoch,
            evidence=evidence,
            metric_used=metric_used,
        )

    def _check_metric(
        self,
        title: str,
        train_y: List[float],
        val_y: List[float],
        is_loss: bool,
    ) -> dict:
        """Check a single metric pair for overfitting signals."""
        evidence = []
        confidence = 0.0
        severity = "none"
        divergence_epoch = None

        # Align lengths
        n = min(len(train_y), len(val_y))
        train_y = train_y[:n]
        val_y = val_y[:n]

        final_train = train_y[-1]
        final_val = val_y[-1]

        # ── Signal 1: train-val gap ──────────────────────────────────────────
        if is_loss:
            # For loss: overfitting if val_loss >> train_loss
            gap = final_val - final_train
            relative_gap = gap / (abs(final_train) + 1e-9)
        else:
            # For accuracy: overfitting if train_acc >> val_acc
            gap = final_train - final_val
            relative_gap = gap / (abs(final_train) + 1e-9)

        if relative_gap > self.gap_threshold_severe:
            severity = "severe"
            confidence = min(0.95, 0.6 + relative_gap)
            evidence.append(
                f"{title}: final train-val gap is {relative_gap:.1%} "
                f"(train={final_train:.4f}, val={final_val:.4f})"
            )
        elif relative_gap > self.gap_threshold_mild:
            severity = "moderate"
            confidence = max(confidence, 0.5 + relative_gap * 2)
            evidence.append(
                f"{title}: train-val gap of {relative_gap:.1%} suggests overfitting"
            )

        # ── Signal 2: val metric divergence (peaks then degrades) ─────────────
        if n >= self.divergence_window * 2:
            window = self.divergence_window
            if is_loss:
                best_idx = val_y.index(min(val_y))
                tail_mean = sum(val_y[-window:]) / window
                best_val = val_y[best_idx]
                degradation = (tail_mean - best_val) / (abs(best_val) + 1e-9)
            else:
                best_idx = val_y.index(max(val_y))
                tail_mean = sum(val_y[-window:]) / window
                best_val = val_y[best_idx]
                degradation = (best_val - tail_mean) / (abs(best_val) + 1e-9)

            if degradation > 0.03 and best_idx < n - window:
                divergence_epoch = best_idx
                confidence = max(confidence, 0.55 + degradation)
                if severity == "none":
                    severity = "mild"
                evidence.append(
                    f"{title}: val metric peaked at epoch {best_idx} "
                    f"then degraded by {degradation:.1%}"
                )

        # ── Signal 3: train consistently better across all epochs ─────────────
        if n >= 5:
            if is_loss:
                train_better_count = sum(
                    1 for t, v in zip(train_y[-5:], val_y[-5:]) if t < v
                )
            else:
                train_better_count = sum(
                    1 for t, v in zip(train_y[-5:], val_y[-5:]) if t > v
                )
            if train_better_count >= 4:
                confidence = max(confidence, 0.4)
                if severity == "none":
                    severity = "mild"
                evidence.append(
                    f"{title}: train consistently outperforms val over last 5 epochs"
                )

        confidence = min(confidence, 1.0)
        return {
            "severity": severity,
            "confidence": confidence,
            "gap": gap,
            "divergence_epoch": divergence_epoch,
            "evidence": evidence,
        }

    def _find_series(self, series_dict: dict, name_set: set):
        """Find a series by matching its name against a set of known names."""
        for name, series in series_dict.items():
            if name.lower() in name_set or any(n in name.lower() for n in name_set):
                return series
        return None

    def _get_priority_metrics(self, scalars: dict) -> List[str]:
        """Return metric titles in priority order (loss first)."""
        titles = list(scalars.keys())
        loss_titles = [t for t in titles if "loss" in t.lower()]
        other_titles = [t for t in titles if "loss" not in t.lower()]
        return loss_titles + other_titles
