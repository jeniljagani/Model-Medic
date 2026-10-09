"""
Unit tests for modelmedic.diagnosis

Tests all diagnosis modules without requiring a ClearML server.
All data is synthetic.
"""
import pytest
from modelmedic.diagnosis.overfitting import OverfittingDetector
from modelmedic.diagnosis.underfitting import UnderfittingDetector
from modelmedic.diagnosis.metric_analysis import MetricAnalyzer
from modelmedic.diagnosis.training_stability import TrainingStabilityAnalyzer
from modelmedic.diagnosis.engine import DiagnosisEngine
from modelmedic.integration.experiment_fetcher import ExperimentData, ScalarSeries


# ── Fixtures ─────────────────────────────────────────────────────────────────

def make_scalars(train_loss, val_loss=None, train_acc=None, val_acc=None):
    """Build a scalars dict from raw lists."""
    scalars = {}
    epochs = list(range(len(train_loss)))

    if train_loss:
        scalars.setdefault("loss", {})
        scalars["loss"]["train"] = ScalarSeries("loss", "train", epochs, list(train_loss))
    if val_loss:
        scalars.setdefault("loss", {})
        scalars["loss"]["val"] = ScalarSeries("loss", "val", epochs[:len(val_loss)], list(val_loss))
    if train_acc:
        scalars.setdefault("accuracy", {})
        scalars["accuracy"]["train"] = ScalarSeries("accuracy", "train", epochs, list(train_acc))
    if val_acc:
        scalars.setdefault("accuracy", {})
        scalars["accuracy"]["val"] = ScalarSeries("accuracy", "val", epochs[:len(val_acc)], list(val_acc))

    return scalars


def make_experiment(scalars, task_id="test-task", task_name="Test Experiment"):
    """Build a minimal ExperimentData for testing."""
    return ExperimentData(
        task_id=task_id,
        task_name=task_name,
        project_name="Test Project",
        task_type="training",
        status="completed",
        scalars=scalars,
    )


# ── OverfittingDetector ───────────────────────────────────────────────────────

class TestOverfittingDetector:

    def test_no_overfitting_clean_run(self):
        """Clean convergence — train and val loss track closely together."""
        # Gap is <3% throughout — should not trigger overfitting
        train = [0.90, 0.70, 0.50, 0.35, 0.28, 0.24, 0.22]
        val   = [0.91, 0.71, 0.51, 0.36, 0.29, 0.25, 0.23]
        scalars = make_scalars(train, val)
        result = OverfittingDetector(gap_threshold_mild=0.05).analyze(scalars)
        assert result.severity in ("none", "mild"), (
            f"Expected no/mild overfitting, got {result.severity}"
        )

    def test_severe_overfitting(self):
        """Train loss drops, val loss grows significantly."""
        train = [0.9, 0.6, 0.3, 0.1, 0.05, 0.02, 0.01]
        val   = [0.9, 0.8, 0.85, 0.90, 0.95, 1.0, 1.1]
        scalars = make_scalars(train, val)
        result = OverfittingDetector().analyze(scalars)
        assert result.detected, "Expected overfitting to be detected"
        assert result.severity in ("moderate", "severe"), (
            f"Expected moderate/severe, got {result.severity}"
        )

    def test_no_val_metrics_no_detection(self):
        """Without val metrics, overfitting cannot be detected."""
        train = [0.9, 0.6, 0.3, 0.1, 0.05]
        scalars = make_scalars(train)  # no val
        result = OverfittingDetector().analyze(scalars)
        assert not result.detected

    def test_divergence_detection(self):
        """Val metric peaks at epoch 3 then degrades."""
        train = [0.9, 0.7, 0.5, 0.3, 0.2, 0.15, 0.12]
        val   = [0.9, 0.75, 0.6, 0.55, 0.65, 0.75, 0.85]  # peaks at epoch 3
        scalars = make_scalars(train, val)
        result = OverfittingDetector().analyze(scalars)
        assert result.detected

    def test_result_fields_populated(self):
        """Result should always have all expected fields."""
        scalars = make_scalars([0.5, 0.4, 0.3], [0.6, 0.7, 0.8])
        result = OverfittingDetector().analyze(scalars)
        assert isinstance(result.detected, bool)
        assert isinstance(result.severity, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.evidence, list)


# ── UnderfittingDetector ──────────────────────────────────────────────────────

class TestUnderfittingDetector:

    def test_no_underfitting_good_accuracy(self):
        """Model trains well — high accuracy, low loss."""
        train_loss = [0.9, 0.5, 0.2, 0.1, 0.05]
        scalars = make_scalars(train_loss)
        result = UnderfittingDetector(min_expected_loss=0.3).analyze(scalars)
        assert result.severity in ("none", "mild")

    def test_underfitting_high_loss(self):
        """Model never gets below the loss threshold."""
        train_loss = [0.9, 0.88, 0.87, 0.86, 0.85, 0.85]
        scalars = make_scalars(train_loss)
        result = UnderfittingDetector(min_expected_loss=0.5).analyze(scalars)
        assert result.detected
        assert result.severity in ("moderate", "severe")

    def test_flat_curve_detected(self):
        """Flat loss curve = stalled training = underfitting."""
        train_loss = [0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8]
        scalars = make_scalars(train_loss)
        result = UnderfittingDetector().analyze(scalars)
        assert result.detected

    def test_insufficient_improvement(self):
        """Negligible improvement from first to last epoch."""
        train_loss = [0.80, 0.79, 0.785, 0.783, 0.782, 0.781]
        scalars = make_scalars(train_loss)
        result = UnderfittingDetector(min_improvement_ratio=0.05).analyze(scalars)
        assert result.detected


# ── MetricAnalyzer ────────────────────────────────────────────────────────────

class TestMetricAnalyzer:

    def test_val_metrics_present(self):
        scalars = make_scalars([0.9, 0.6, 0.3], [0.9, 0.7, 0.4])
        result = MetricAnalyzer().analyze(scalars)
        assert result.has_validation_metrics

    def test_no_val_metrics_warning(self):
        scalars = make_scalars([0.9, 0.6, 0.3])  # no val
        result = MetricAnalyzer().analyze(scalars)
        assert not result.has_validation_metrics
        assert len(result.warnings) > 0

    def test_empty_scalars(self):
        result = MetricAnalyzer().analyze({})
        assert len(result.warnings) > 0
        assert result.total_epochs == 0

    def test_nan_detection(self):
        import math
        scalars = {
            "loss": {
                "train": ScalarSeries("loss", "train", [0, 1, 2], [0.9, float("nan"), 0.5])
            }
        }
        result = MetricAnalyzer().analyze(scalars)
        assert result.nan_inf_detected


# ── TrainingStabilityAnalyzer ─────────────────────────────────────────────────

class TestTrainingStabilityAnalyzer:

    def test_stable_smooth_curve(self):
        # Values in a tight range so CV is low (stable)
        train = [0.50, 0.48, 0.46, 0.44, 0.43, 0.42, 0.41]
        scalars = make_scalars(train)
        result = TrainingStabilityAnalyzer(oscillation_threshold=0.5).analyze(scalars)
        assert result.is_stable

    def test_spike_detected(self):
        train = [0.5, 0.4, 0.35, 5.0, 0.35, 0.3, 0.25]  # spike at step 3
        scalars = make_scalars(train)
        result = TrainingStabilityAnalyzer(spike_threshold=0.5).analyze(scalars)
        assert result.spike_detected

    def test_divergence_detected(self):
        train = [0.5, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]  # increasing
        scalars = make_scalars(train)
        result = TrainingStabilityAnalyzer(divergence_window=5).analyze(scalars)
        assert result.is_diverging

    def test_empty_scalars_no_crash(self):
        result = TrainingStabilityAnalyzer().analyze({})
        assert result.is_stable  # default to stable when no data


# ── DiagnosisEngine ───────────────────────────────────────────────────────────

class TestDiagnosisEngine:

    def test_healthy_experiment(self):
        """Clean experiment — close train/val tracking, stable curve."""
        # Very tight train/val gap and very smooth curve
        train = [0.50, 0.48, 0.46, 0.44, 0.43, 0.42, 0.41]
        val   = [0.51, 0.49, 0.47, 0.45, 0.44, 0.43, 0.42]
        scalars = make_scalars(train, val)
        experiment = make_experiment(scalars)
        report = DiagnosisEngine().run(experiment)
        assert report.overall_health in ("healthy", "warning")
        assert report.experiment_id == "test-task"

    def test_overfitting_experiment_detected(self):
        """Overfitting experiment should produce findings."""
        train = [0.9, 0.5, 0.2, 0.05, 0.01, 0.005]
        val   = [0.9, 0.8, 0.85, 0.92, 1.0, 1.1]
        scalars = make_scalars(train, val)
        experiment = make_experiment(scalars)
        report = DiagnosisEngine().run(experiment)
        categories = [f.category for f in report.findings]
        assert "overfitting" in categories

    def test_report_summary_is_string(self):
        scalars = make_scalars([0.9, 0.6, 0.3], [0.9, 0.7, 0.4])
        experiment = make_experiment(scalars)
        report = DiagnosisEngine().run(experiment)
        summary = report.summary()
        assert isinstance(summary, str)
        assert "ModelMedic" in summary

    def test_report_to_dict_serializable(self):
        import json
        scalars = make_scalars([0.9, 0.6, 0.3], [0.9, 0.7, 0.4])
        experiment = make_experiment(scalars)
        report = DiagnosisEngine().run(experiment)
        d = report.to_dict()
        # Should be JSON-serializable
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

    def test_findings_sorted_by_severity(self):
        """Most severe findings should come first."""
        train = [0.9, 0.5, 0.2, 0.05, 0.01]
        val   = [0.9, 0.8, 0.85, 0.95, 1.1]
        scalars = make_scalars(train, val)
        experiment = make_experiment(scalars)
        report = DiagnosisEngine().run(experiment)
        severity_order = {"severe": 3, "moderate": 2, "mild": 1, "none": 0}
        for i in range(len(report.findings) - 1):
            assert (
                severity_order[report.findings[i].severity]
                >= severity_order[report.findings[i + 1].severity]
            )
