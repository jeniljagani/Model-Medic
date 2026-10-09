"""
modelmedic.diagnosis.training_stability
=========================================
Detects training instability — loss spikes, oscillation, divergence.

Unstable training signals:
  - High variance in loss curve (oscillating)
  - Sudden loss spike (exploding gradients)
  - Loss is increasing over time (diverging)
  - Loss is NaN (already caught by MetricAnalyzer)
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StabilityResult:
    is_stable: bool
    detected_issues: List[str]  # "oscillation" | "spike" | "divergence"
    evidence: List[str]
    oscillation_score: Optional[float]  # higher = more oscillation
    spike_detected: bool
    is_diverging: bool
    metric_used: Optional[str]


class TrainingStabilityAnalyzer:
    """
    Analyzes training metric curves for stability problems.

    Parameters
    ----------
    spike_threshold : float
        A single-step increase in loss by this fraction triggers spike detection.
    oscillation_threshold : float
        Coefficient of variation above this is considered oscillating.
    divergence_window : int
        Epochs at the end of training to check for increasing trend.
    """

    LOSS_NAMES = {"loss", "train_loss", "training_loss"}

    def __init__(
        self,
        spike_threshold: float = 0.5,
        oscillation_threshold: float = 0.3,
        divergence_window: int = 5,
    ) -> None:
        self.spike_threshold = spike_threshold
        self.oscillation_threshold = oscillation_threshold
        self.divergence_window = divergence_window

    def analyze(self, scalars: Dict[str, Dict]) -> StabilityResult:
        """Run stability analysis, focusing on loss metrics."""
        # Focus on loss metrics for stability
        loss_titles = [
            t for t in scalars.keys() if "loss" in t.lower()
        ]
        if not loss_titles:
            loss_titles = list(scalars.keys())

        best_result = None

        for title in loss_titles:
            series_dict = scalars.get(title, {})
            # Prefer train loss
            train_series = None
            for name, s in series_dict.items():
                if any(n in name.lower() for n in {"train", "training"}):
                    train_series = s
                    break
            if train_series is None and series_dict:
                train_series = next(iter(series_dict.values()))

            if train_series is None:
                continue

            y = list(
                train_series.y if hasattr(train_series, "y")
                else train_series.get("y", [])
            )
            if len(y) < 4:
                continue

            result = self._check_stability(title, y)
            if best_result is None or len(result["evidence"]) > len(best_result["evidence"]):
                best_result = result

        if best_result is None:
            return StabilityResult(
                is_stable=True,
                detected_issues=[],
                evidence=["Insufficient data for stability analysis"],
                oscillation_score=None,
                spike_detected=False,
                is_diverging=False,
                metric_used=None,
            )

        issues = []
        if best_result["oscillation_score"] and best_result["oscillation_score"] > self.oscillation_threshold:
            issues.append("oscillation")
        if best_result["spike_detected"]:
            issues.append("spike")
        if best_result["is_diverging"]:
            issues.append("divergence")

        return StabilityResult(
            is_stable=len(issues) == 0,
            detected_issues=issues,
            evidence=best_result["evidence"],
            oscillation_score=best_result["oscillation_score"],
            spike_detected=best_result["spike_detected"],
            is_diverging=best_result["is_diverging"],
            metric_used=best_result["title"],
        )

    def _check_stability(self, title: str, y: List[float]) -> dict:
        evidence = []
        spike_detected = False
        is_diverging = False

        # ── Oscillation: high coefficient of variation ─────────────────────────
        try:
            mean_y = statistics.mean(y)
            std_y = statistics.stdev(y)
            cv = std_y / (abs(mean_y) + 1e-9)
        except Exception:
            cv = 0.0

        if cv > self.oscillation_threshold:
            evidence.append(
                f"{title}: high oscillation detected "
                f"(coefficient of variation={cv:.2f}). "
                f"Consider reducing learning rate or adding gradient clipping."
            )

        # ── Spike: sudden large increase ────────────────────────────────────────
        for i in range(1, len(y)):
            if y[i - 1] > 1e-9:
                step_change = (y[i] - y[i - 1]) / abs(y[i - 1])
                if step_change > self.spike_threshold:
                    spike_detected = True
                    evidence.append(
                        f"{title}: loss spike at step {i} "
                        f"({y[i-1]:.4f} → {y[i]:.4f}, "
                        f"+{step_change:.1%}). "
                        f"Possible cause: exploding gradients or bad batch."
                    )
                    break  # report first spike only

        # ── Divergence: increasing trend in tail ──────────────────────────────
        w = min(self.divergence_window, len(y) // 2)
        if w >= 2:
            tail = y[-w:]
            increasing = sum(
                1 for i in range(1, len(tail)) if tail[i] > tail[i - 1]
            )
            if increasing >= len(tail) - 1:
                is_diverging = True
                evidence.append(
                    f"{title}: loss is monotonically increasing in the last "
                    f"{w} steps — possible divergence. "
                    f"Reduce learning rate or check data pipeline."
                )

        return {
            "title": title,
            "oscillation_score": cv,
            "spike_detected": spike_detected,
            "is_diverging": is_diverging,
            "evidence": evidence,
        }
