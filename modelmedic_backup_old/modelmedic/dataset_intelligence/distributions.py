from __future__ import annotations

import logging
import pandas as pd
from .models import DistributionFindings, Severity

logger = logging.getLogger(__name__)

class DistributionAnalyzer:
    """Analyzes numerical columns for skewness, heavy tails, and near-zero variance."""

    def __init__(
        self,
        skew_threshold: float = 2.0,
        kurtosis_threshold: float = 7.0,
    ) -> None:
        self.skew_threshold = skew_threshold
        self.kurtosis_threshold = kurtosis_threshold

    def analyze(self, df: pd.DataFrame) -> DistributionFindings:
        numeric_cols = df.select_dtypes(include=[float, int, "number"]).columns
        if len(numeric_cols) == 0:
            return DistributionFindings(
                skewed_columns=[],
                heavy_tail_columns=[],
                zero_variance_columns=[],
                severity=Severity.INFO,
                evidence="No numeric columns.",
                explanation="Distributions are only evaluated on numeric data.",
                recommendations=[]
            )

        skewed_columns = []
        heavy_tail_columns = []
        zero_variance_columns = []
        warnings = []
        recommendations = []

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 3:
                continue

            var = series.var()
            if var == 0 or pd.isna(var):
                zero_variance_columns.append(col)
                continue

            skew = series.skew()
            kurt = series.kurtosis()

            if pd.notna(skew) and abs(skew) > self.skew_threshold:
                skewed_columns.append(col)
            if pd.notna(kurt) and kurt > self.kurtosis_threshold:
                heavy_tail_columns.append(col)

        severity = Severity.INFO
        if zero_variance_columns:
            severity = Severity.MEDIUM
            warnings.append(f"{len(zero_variance_columns)} columns have zero variance.")
            recommendations.append(f"Drop zero-variance columns: {', '.join(zero_variance_columns[:5])}")

        if skewed_columns:
            severity = max(severity, Severity.LOW)
            warnings.append(f"{len(skewed_columns)} columns are highly skewed.")
            recommendations.append("Consider log transformations (e.g. log1p) or QuantileTransformer for skewed columns.")

        if heavy_tail_columns:
            severity = max(severity, Severity.LOW)
            warnings.append(f"{len(heavy_tail_columns)} columns have heavy tails (high kurtosis).")
            recommendations.append("Robust scaling is recommended for heavy-tailed distributions.")

        evidence = " | ".join(warnings) if warnings else "Numeric distributions appear normal."
        explanation = "Machine learning models, especially linear ones, assume normal distributions. Skew and heavy tails degrade performance."

        return DistributionFindings(
            skewed_columns=skewed_columns,
            heavy_tail_columns=heavy_tail_columns,
            zero_variance_columns=zero_variance_columns,
            severity=severity,
            evidence=evidence,
            explanation=explanation,
            recommendations=recommendations
        )
