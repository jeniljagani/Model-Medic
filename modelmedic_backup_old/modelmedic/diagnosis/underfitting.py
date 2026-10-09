"""
modelmedic.diagnosis.underfitting
===================================
Detects underfitting / high-bias from metric history.

Underfitting = model too simple, fails to learn training data.
Signals:
  - Training loss stays high / accuracy stays low
  - Very small gap between train and val (both perform poorly)
  - No improvement trend across epochs
  - Final metric below expected baseline
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UnderfittingResult:
    detected: bool
    severity: str           # "none" | "mild" | "moderate" | "severe"
    confidence: float       # 0.0 – 1.0
    final_train_metric: Optional[float]
    improvement_rate: Optional[float]  # how much the metric improved over training
    evidence: List[str]
    metric_used: Optional[str]


class UnderfittingDetector:
    """
    Detects underfitting from scalar metric history.

    Parameters
    ----------
    min_expected_loss : float
        If final train loss exceeds this, flag as underfitting.
    min_accuracy_threshold : float
        If final train accuracy is below this for a classification task,
        flag as underfitting.
    min_improvement_ratio : float
        Minimum fractional improvement from first to last epoch.
        If improvement is below this, it's a sign of underfitting.
    """

    TRAIN_NAMES = {"train", "training", "train_loss", "train_acc"}

    def __init__(
        self,
        min_expected_loss: float = 0.5,
        min_accuracy_threshold: float = 0.6,
        min_improvement_ratio: float = 0.05,
    ) -> None:
        self.min_expected_loss = min_expected_loss
        self.min_accuracy_threshold = min_accuracy_threshold
        self.min_improvement_ratio = min_improvement_ratio

    def analyze(self, scalars: Dict[str, Dict]) -> UnderfittingResult:
        """Run underfitting analysis on a scalars dict."""
        evidence = []
        max_severity = "none"
        max_confidence = 0.0
        metric_used = None
        final_train_metric = None
        improvement_rate = None

        priority_metrics = self._get_priority_metrics(scalars)

        for title in priority_metrics:
            series_dict = scalars.get(title, {})
            train_series = self._find_series(series_dict, self.TRAIN_NAMES)

            if train_series is None:
                continue

            train_y = list(
                train_series.y if hasattr(train_series, "y")
                else train_series.get("y", [])
            )

            if len(train_y) < 3:
                continue

            is_loss = "loss" in title.lower()
            result = self._check_metric(
                title=title,
                train_y=train_y,
                is_loss=is_loss,
            )

            if result["confidence"] > max_confidence:
                max_confidence = result["confidence"]
                max_severity = result["severity"]
                final_train_metric = result["final_value"]
                improvement_rate = result["improvement_rate"]
                metric_used = title
                evidence = result["evidence"]

        return UnderfittingResult(
            detected=max_severity != "none",
            severity=max_severity,
            confidence=max_confidence,
            final_train_metric=final_train_metric,
            improvement_rate=improvement_rate,
            evidence=evidence,
            metric_used=metric_used,
        )

    def _check_metric(
        self,
        title: str,
        train_y: List[float],
        is_loss: bool,
    ) -> dict:
        evidence = []
        confidence = 0.0
        severity = "none"
        final_value = train_y[-1]
        first_value = train_y[0]

        # ── Signal 1: poor absolute performance ───────────────────────────────
        if is_loss:
            if final_value > self.min_expected_loss:
                severity = "moderate"
                confidence = min(0.8, 0.4 + (final_value - self.min_expected_loss))
                evidence.append(
                    f"{title}: final train loss {final_value:.4f} "
                    f"is still high (threshold: {self.min_expected_loss})"
                )
        else:
            if final_value < self.min_accuracy_threshold:
                severity = "moderate"
                confidence = min(
                    0.8,
                    0.4 + (self.min_accuracy_threshold - final_value),
                )
                evidence.append(
                    f"{title}: final train accuracy {final_value:.4f} "
                    f"is below threshold ({self.min_accuracy_threshold})"
                )

        # ── Signal 2: insufficient improvement over training ──────────────────
        if abs(first_value) > 1e-9:
            if is_loss:
                improvement = (first_value - final_value) / abs(first_value)
            else:
                improvement = (final_value - first_value) / abs(first_value)

            if improvement < self.min_improvement_ratio:
                if severity == "none":
                    severity = "mild"
                confidence = max(confidence, 0.45)
                evidence.append(
                    f"{title}: only {improvement:.1%} improvement over "
                    f"{len(train_y)} training steps — model is not learning"
                )
        else:
            improvement = 0.0

        # ── Signal 3: flat training curve ─────────────────────────────────────
        if len(train_y) >= 5:
            tail = train_y[-5:]
            tail_variance = sum((v - sum(tail) / len(tail)) ** 2 for v in tail) / len(tail)
            if tail_variance < 1e-6:
                if severity == "none":
                    severity = "mild"
                confidence = max(confidence, 0.4)
                evidence.append(
                    f"{title}: training curve is completely flat in last 5 epochs "
                    f"(variance={tail_variance:.2e}) — learning has stalled"
                )

        confidence = min(confidence, 1.0)
        return {
            "severity": severity,
            "confidence": confidence,
            "final_value": final_value,
            "improvement_rate": improvement,
            "evidence": evidence,
        }

    def _find_series(self, series_dict: dict, name_set: set):
        for name, series in series_dict.items():
            if name.lower() in name_set or any(n in name.lower() for n in name_set):
                return series
        return None

    def _get_priority_metrics(self, scalars: dict) -> List[str]:
        titles = list(scalars.keys())
        loss_titles = [t for t in titles if "loss" in t.lower()]
        other_titles = [t for t in titles if "loss" not in t.lower()]
        return loss_titles + other_titles
