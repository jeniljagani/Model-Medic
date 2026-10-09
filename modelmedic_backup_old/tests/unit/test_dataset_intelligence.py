"""
Unit tests for modelmedic.dataset_intelligence

Tests all dataset analysis modules with synthetic DataFrames.
"""
import pytest
import pandas as pd
import numpy as np

from modelmedic.dataset_intelligence.missing_values import MissingValueDetector
from modelmedic.dataset_intelligence.class_balance import ClassBalanceAnalyzer
from modelmedic.dataset_intelligence.outliers import OutlierDetector
from modelmedic.dataset_intelligence.analyzer import DatasetAnalyzer
from modelmedic.dataset_intelligence.models import Severity

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def clean_df():
    """Clean balanced DataFrame with no issues."""
    np.random.seed(42)
    return pd.DataFrame({
        "feature_a": np.random.normal(0, 1, 200),
        "feature_b": np.random.normal(5, 2, 200),
        "feature_c": np.random.randint(0, 10, 200).astype(float),
        "label": np.random.choice(["cat", "dog"], 200),
    })

@pytest.fixture
def missing_df():
    """DataFrame with significant missing values."""
    df = pd.DataFrame({
        "good_col": range(100),
        "some_missing": [None if i % 5 == 0 else i for i in range(100)],
        "mostly_missing": [None if i > 20 else i for i in range(100)],  # 80% missing
        "completely_missing": [None] * 100
    })
    return df

@pytest.fixture
def imbalanced_df():
    """DataFrame with severe class imbalance."""
    return pd.DataFrame({
        "feature": range(1100),
        "label": ["majority"] * 1000 + ["minority"] * 100,
    })

@pytest.fixture
def outlier_df():
    """DataFrame with clear outliers."""
    np.random.seed(42)
    data = np.random.normal(0, 1, 100)
    data[0] = 100.0   # extreme outlier
    data[1] = -100.0  # extreme outlier
    return pd.DataFrame({"values": data, "normal": np.random.normal(0, 1, 100)})


# ── MissingValueDetector ──────────────────────────────────────────────────────

class TestMissingValueDetector:

    def test_no_missing(self, clean_df):
        result = MissingValueDetector().analyze(clean_df)
        assert result.total_missing_cells == 0
        assert result.missing_ratio == 0.0

    def test_detects_missing(self, missing_df):
        result = MissingValueDetector().analyze(missing_df)
        assert result.total_missing_cells > 0
        assert "mostly_missing" in result.high_missing_columns
        assert "completely_missing" in result.completely_missing_columns
        assert result.severity == Severity.CRITICAL

    def test_generates_recommendations(self, missing_df):
        result = MissingValueDetector().analyze(missing_df)
        assert len(result.recommendations) > 0


# ── ClassBalanceAnalyzer ──────────────────────────────────────────────────────

class TestClassBalanceAnalyzer:

    def test_balanced_dataset(self, clean_df):
        result = ClassBalanceAnalyzer().analyze(clean_df, "label")
        assert result.severity == Severity.INFO
        assert result.imbalance_ratio < 2.0

    def test_severe_imbalance(self, imbalanced_df):
        result = ClassBalanceAnalyzer().analyze(imbalanced_df, "label")
        assert result.severity in (Severity.HIGH, Severity.MEDIUM)
        assert result.imbalance_ratio >= 9.0

    def test_correct_class_counts(self, imbalanced_df):
        result = ClassBalanceAnalyzer().analyze(imbalanced_df, "label")
        assert result.class_counts["majority"] == 1000
        assert result.class_counts["minority"] == 100

    def test_missing_column_graceful(self, clean_df):
        result = ClassBalanceAnalyzer().analyze(clean_df, "nonexistent_column")
        assert result.task_type == "unknown"

    def test_generates_recommendations(self, imbalanced_df):
        result = ClassBalanceAnalyzer().analyze(imbalanced_df, "label")
        assert len(result.recommendations) > 0


# ── OutlierDetector ───────────────────────────────────────────────────────────

class TestOutlierDetector:

    def test_no_outliers_in_clean_data(self, clean_df):
        result = OutlierDetector(flag_threshold=0.05).analyze(
            clean_df.select_dtypes(include="number")
        )
        assert isinstance(result.outlier_fraction, float)

    def test_detects_extreme_outliers(self, outlier_df):
        result = OutlierDetector().analyze(outlier_df)
        assert "values" in result.columns_with_outliers

    def test_outlier_count_reasonable(self, outlier_df):
        result = OutlierDetector().analyze(outlier_df)
        assert result.total_outlier_rows >= 2

    def test_generates_recommendations(self, outlier_df):
        result = OutlierDetector().analyze(outlier_df)
        assert len(result.recommendations) > 0


# ── DatasetAnalyzer (orchestrator) ────────────────────────────────────────────

class TestDatasetAnalyzer:

    def test_clean_dataset_good_quality(self, clean_df):
        report = DatasetAnalyzer().analyze(clean_df, target_column="label")
        assert report.health_score.score >= 90
        assert report.summary is not None

    def test_all_sub_reports_present(self, clean_df):
        report = DatasetAnalyzer().analyze(clean_df, target_column="label")
        assert report.missing_data is not None
        assert report.class_balance is not None
        assert report.outliers is not None
        assert report.distributions is not None
        assert report.correlations is not None
        assert report.multicollinearity is not None
        assert report.target_analysis is not None
        assert report.leakage is not None

    def test_no_target_column_skips_balance(self, clean_df):
        report = DatasetAnalyzer().analyze(clean_df)
        assert report.class_balance is None
        assert report.target_analysis is None

    def test_summary_is_string(self, clean_df):
        report = DatasetAnalyzer().analyze(clean_df, target_column="label")
        summary_str = report.get_report_summary()
        assert isinstance(summary_str, str)
        assert "ModelMedic" in summary_str

    def test_to_dict_serializable(self, clean_df):
        import json
        report = DatasetAnalyzer().analyze(clean_df, target_column="label")
        d = report.to_dict()
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

    def test_poor_quality_flagged(self, missing_df, imbalanced_df):
        df = pd.DataFrame({
            "a": [None] * 80 + list(range(20)),
            "b": [None] * 70 + list(range(30)),
            "c": [0] * 100,  # constant column
            "label": ["majority"] * 95 + ["minority"] * 5,
        })
        report = DatasetAnalyzer().analyze(df, target_column="label")
        assert report.health_score.score < 80
        assert len(report.critical_issues) > 0 or len(report.warnings) > 0


# ── Edge Cases ─────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_dataset(self):
        df = pd.DataFrame(columns=["a", "b", "label"])
        report = DatasetAnalyzer().analyze(df, target_column="label")
        assert report.health_score.score < 50
        assert "0 rows" in str(report.critical_issues) or "0 rows" in report.get_report_summary()

    def test_single_row_dataset(self):
        df = pd.DataFrame({"a": [1.0], "b": [2.0], "label": ["cat"]})
        report = DatasetAnalyzer().analyze(df, target_column="label")
        assert report.health_score.score < 100

    def test_infinite_values(self):
        df = pd.DataFrame({
            "a": [np.inf, -np.inf, 1.0, 2.0],
            "b": [1, 2, 3, 4],
            "label": ["cat", "dog", "cat", "dog"]
        })
        report = DatasetAnalyzer().analyze(df, target_column="label")
        assert report.health_score.score < 100

