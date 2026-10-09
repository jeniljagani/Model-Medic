"""
modelmedic.diagnosis.engine
=============================
DiagnosisEngine — orchestrates all diagnosis modules and produces
a unified DiagnosisReport for a ClearML experiment.

Usage
-----
    from modelmedic.integration import ExperimentFetcher
    from modelmedic.diagnosis import DiagnosisEngine

    fetcher = ExperimentFetcher()
    experiment = fetcher.fetch("your-task-id")

    engine = DiagnosisEngine()
    report = engine.run(experiment)
    print(report.summary())
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from ..integration.experiment_fetcher import ExperimentData
from .overfitting import OverfittingDetector, OverfittingResult
from .underfitting import UnderfittingDetector, UnderfittingResult
from .metric_analysis import MetricAnalyzer, MetricAnalysisResult
from .training_stability import TrainingStabilityAnalyzer, StabilityResult

logger = logging.getLogger(__name__)

# Severity ranking for sorting
_SEVERITY_ORDER = {"severe": 3, "moderate": 2, "mild": 1, "none": 0}


@dataclass
class DiagnosisFinding:
    """A single diagnosed problem."""
    category: str       # "overfitting" | "underfitting" | "instability" | "data_quality"
    severity: str       # "severe" | "moderate" | "mild"
    confidence: float   # 0.0 – 1.0
    title: str          # short problem title
    description: str    # human-readable explanation
    evidence: List[str] # specific data evidence
    recommendations: List[str]  # immediate action suggestions


@dataclass
class DiagnosisReport:
    """
    Full diagnosis result for one ClearML experiment.

    Attributes
    ----------
    experiment_id : str
        ClearML task ID that was diagnosed.
    experiment_name : str
        Human-readable task name.
    findings : list[DiagnosisFinding]
        All detected problems, sorted by severity (worst first).
    metric_analysis : MetricAnalysisResult
        Summary of metric health.
    overfitting : OverfittingResult
    underfitting : UnderfittingResult
    stability : StabilityResult
    overall_health : str
        "healthy" | "warning" | "critical"
    """
    experiment_id: str
    experiment_name: str
    project_name: str
    web_url: Optional[str]

    findings: List[DiagnosisFinding] = field(default_factory=list)
    metric_analysis: Optional[MetricAnalysisResult] = None
    overfitting: Optional[OverfittingResult] = None
    underfitting: Optional[UnderfittingResult] = None
    stability: Optional[StabilityResult] = None

    overall_health: str = "healthy"  # "healthy" | "warning" | "critical"

    def summary(self) -> str:
        """Return a human-readable text summary of the diagnosis."""
        lines = [
            "=" * 60,
            f"  ModelMedic Diagnosis Report",
            "=" * 60,
            f"  Experiment : {self.experiment_name}",
            f"  ID         : {self.experiment_id}",
            f"  Project    : {self.project_name}",
            f"  Health     : {self.overall_health.upper()}",
            f"  URL        : {self.web_url or 'N/A'}",
            "=" * 60,
        ]

        if not self.findings:
            lines.append("  No problems detected. Experiment looks healthy!")
        else:
            lines.append(f"  {len(self.findings)} problem(s) found:\n")
            for i, f in enumerate(self.findings, 1):
                lines.append(
                    f"  [{i}] [{f.severity.upper()}] {f.title} "
                    f"(confidence: {f.confidence:.0%})"
                )
                lines.append(f"      {f.description}")
                for ev in f.evidence:
                    lines.append(f"      - Evidence: {ev}")
                lines.append("      Recommendations:")
                for rec in f.recommendations:
                    lines.append(f"        → {rec}")
                lines.append("")

        if self.metric_analysis and self.metric_analysis.warnings:
            lines.append("  Metric Warnings:")
            for w in self.metric_analysis.warnings:
                lines.append(f"    ! {w}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict for API responses."""
        return {
            "experiment_id": self.experiment_id,
            "experiment_name": self.experiment_name,
            "project_name": self.project_name,
            "web_url": self.web_url,
            "overall_health": self.overall_health,
            "findings": [
                {
                    "category": f.category,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "title": f.title,
                    "description": f.description,
                    "evidence": f.evidence,
                    "recommendations": f.recommendations,
                }
                for f in self.findings
            ],
            "metric_summary": {
                "has_validation": self.metric_analysis.has_validation_metrics
                if self.metric_analysis else None,
                "total_epochs": self.metric_analysis.total_epochs
                if self.metric_analysis else None,
                "warnings": self.metric_analysis.warnings
                if self.metric_analysis else [],
            },
        }


class DiagnosisEngine:
    """
    Orchestrates all ModelMedic diagnosis modules for one experiment.

    Runs:
      1. MetricAnalyzer  — validates metric health
      2. OverfittingDetector
      3. UnderfittingDetector
      4. TrainingStabilityAnalyzer

    Then synthesizes all findings into a DiagnosisReport.

    Usage
    -----
        engine = DiagnosisEngine()
        report = engine.run(experiment_data)
    """

    def __init__(self) -> None:
        self._metric_analyzer = MetricAnalyzer()
        self._overfit_detector = OverfittingDetector()
        self._underfit_detector = UnderfittingDetector()
        self._stability_analyzer = TrainingStabilityAnalyzer()

    def run(self, experiment: ExperimentData) -> DiagnosisReport:
        """
        Run all diagnosis modules on the given experiment data.

        Parameters
        ----------
        experiment : ExperimentData
            Fetched from ExperimentFetcher.fetch()

        Returns
        -------
        DiagnosisReport
        """
        logger.info(
            "Running diagnosis for experiment: %s (%s)",
            experiment.task_name,
            experiment.task_id,
        )

        scalars = experiment.scalars

        # ── 1. Metric analysis ────────────────────────────────────────────────
        metric_result = self._metric_analyzer.analyze(scalars)

        # ── 2. Overfitting ────────────────────────────────────────────────────
        overfit_result = self._overfit_detector.analyze(scalars)

        # ── 3. Underfitting ───────────────────────────────────────────────────
        underfit_result = self._underfit_detector.analyze(scalars)

        # ── 4. Training stability ─────────────────────────────────────────────
        stability_result = self._stability_analyzer.analyze(scalars)

        # ── 5. Synthesize findings ────────────────────────────────────────────
        findings = []

        if overfit_result.detected:
            findings.append(DiagnosisFinding(
                category="overfitting",
                severity=overfit_result.severity,
                confidence=overfit_result.confidence,
                title="Overfitting Detected",
                description=(
                    f"The model is memorizing the training data and failing to generalize. "
                    f"Train-validation gap on '{overfit_result.metric_used}': "
                    f"{overfit_result.train_val_gap:.4f}."
                    if overfit_result.train_val_gap is not None
                    else "The model appears to be overfitting."
                ),
                evidence=overfit_result.evidence,
                recommendations=self._overfit_recommendations(overfit_result),
            ))

        if underfit_result.detected:
            findings.append(DiagnosisFinding(
                category="underfitting",
                severity=underfit_result.severity,
                confidence=underfit_result.confidence,
                title="Underfitting / High Bias Detected",
                description=(
                    f"The model is not learning enough from the training data. "
                    f"Final train metric on '{underfit_result.metric_used}': "
                    f"{underfit_result.final_train_metric:.4f}."
                    if underfit_result.final_train_metric is not None
                    else "The model appears to be underfitting."
                ),
                evidence=underfit_result.evidence,
                recommendations=self._underfit_recommendations(underfit_result),
            ))

        if not stability_result.is_stable:
            for issue in stability_result.detected_issues:
                findings.append(DiagnosisFinding(
                    category="training_instability",
                    severity="moderate",
                    confidence=0.75,
                    title=f"Training Instability: {issue.title()}",
                    description=self._stability_description(issue),
                    evidence=stability_result.evidence,
                    recommendations=self._stability_recommendations(issue),
                ))

        # Sort by severity (worst first)
        findings.sort(
            key=lambda f: _SEVERITY_ORDER.get(f.severity, 0),
            reverse=True,
        )

        # ── 6. Overall health ─────────────────────────────────────────────────
        overall_health = self._compute_health(findings, metric_result)

        return DiagnosisReport(
            experiment_id=experiment.task_id,
            experiment_name=experiment.task_name,
            project_name=experiment.project_name,
            web_url=experiment.web_url,
            findings=findings,
            metric_analysis=metric_result,
            overfitting=overfit_result,
            underfitting=underfit_result,
            stability=stability_result,
            overall_health=overall_health,
        )

    # ── Recommendation generators ────────────────────────────────────────────

    def _overfit_recommendations(self, result: OverfittingResult) -> List[str]:
        recs = [
            "Add or increase regularization (L1/L2 weight decay).",
            "Use dropout layers to reduce model capacity.",
            "Collect more training data or use data augmentation.",
            "Reduce model complexity (fewer layers or parameters).",
            "Apply early stopping based on validation metric.",
        ]
        if result.divergence_epoch is not None:
            recs.insert(0,
                f"Stop training at epoch {result.divergence_epoch} "
                f"(best validation point)."
            )
        if result.severity == "mild":
            return recs[:3]
        return recs

    def _underfit_recommendations(self, result: UnderfittingResult) -> List[str]:
        recs = [
            "Increase model capacity (more layers, more units).",
            "Train for more epochs.",
            "Increase learning rate or use a learning rate scheduler.",
            "Review feature engineering — add more informative features.",
            "Check data quality and remove noise.",
        ]
        if result.improvement_rate is not None and result.improvement_rate < 0.01:
            recs.insert(0, "Learning rate may be too small — the model is barely moving.")
        return recs

    def _stability_description(self, issue: str) -> str:
        return {
            "oscillation": (
                "The training loss is oscillating significantly between steps. "
                "This typically indicates the learning rate is too high."
            ),
            "spike": (
                "A sudden spike in loss was detected. This is often caused by "
                "exploding gradients, a bad batch of data, or an excessively "
                "high learning rate."
            ),
            "divergence": (
                "The training loss is increasing over time instead of decreasing. "
                "The model is diverging and not converging to a solution."
            ),
        }.get(issue, f"Training instability issue: {issue}")

    def _stability_recommendations(self, issue: str) -> List[str]:
        return {
            "oscillation": [
                "Reduce the learning rate by 5-10x.",
                "Add gradient clipping (clip_grad_norm).",
                "Use a learning rate scheduler (cosine annealing, ReduceLROnPlateau).",
            ],
            "spike": [
                "Add gradient clipping immediately.",
                "Reduce the learning rate.",
                "Inspect the data batch that caused the spike — it may be corrupted.",
            ],
            "divergence": [
                "Stop this training run.",
                "Reduce the learning rate significantly.",
                "Check that loss function and optimizer are configured correctly.",
                "Verify training data is not corrupted.",
            ],
        }.get(issue, ["Investigate the training configuration."])

    def _compute_health(
        self,
        findings: List[DiagnosisFinding],
        metric_result: MetricAnalysisResult,
    ) -> str:
        if not findings and not metric_result.warnings:
            return "healthy"
        severities = [_SEVERITY_ORDER.get(f.severity, 0) for f in findings]
        if severities and max(severities) >= 3:
            return "critical"
        if severities and max(severities) >= 2:
            return "warning"
        if findings or metric_result.warnings:
            return "warning"
        return "healthy"
