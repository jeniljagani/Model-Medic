from __future__ import annotations

import logging
import pandas as pd

from .models import OutlierFindings, Severity

logger = logging.getLogger(__name__)

class OutlierDetector:
    """Detects outliers in numeric columns using IQR and Z-score methods."""

    def __init__(
        self,
        iqr_multiplier: float = 1.5,
        z_score_threshold: float = 3.0,
        flag_threshold: float = 0.01,
    ) -> None:
        self.iqr_multiplier = iqr_multiplier
        self.z_score_threshold = z_score_threshold
        self.flag_threshold = flag_threshold

    def analyze(self, df: pd.DataFrame) -> OutlierFindings:
        numeric_cols = df.select_dtypes(include=[float, int, "number"]).columns
        if len(numeric_cols) == 0:
            return OutlierFindings(
                columns_with_outliers=[],
                total_outlier_rows=0,
                outlier_fraction=0.0,
                severity=Severity.INFO,
                evidence="No numeric columns to evaluate.",
                explanation="Outliers can only be calculated on numeric data.",
                recommendations=[]
            )

        outlier_mask = None
        columns_with_outliers = []
        warnings = []
        recommendations = []

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 4:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            lower = q1 - self.iqr_multiplier * iqr
            upper = q3 + self.iqr_multiplier * iqr
            iqr_mask = (df[col] < lower) | (df[col] > upper)

            mean = float(series.mean())
            std = float(series.std())
            if std > 1e-9:
                z_mask = ((df[col] - mean) / std).abs() > self.z_score_threshold
            else:
                z_mask = iqr_mask.copy()

            combined_mask = iqr_mask | z_mask
            combined_count = int(combined_mask.sum())
            col_fraction = combined_count / max(len(df), 1)

            if col_fraction >= self.flag_threshold:
                columns_with_outliers.append(col)

            if outlier_mask is None:
                outlier_mask = combined_mask
            else:
                outlier_mask = outlier_mask | combined_mask

        total_outlier_rows = int(outlier_mask.sum()) if outlier_mask is not None else 0
        outlier_fraction = total_outlier_rows / max(len(df), 1)

        severity = Severity.INFO
        if outlier_fraction > 0.10:
            severity = Severity.HIGH
            warnings.append(f"High outlier fraction: {outlier_fraction:.1%} of rows have statistical outliers.")
            recommendations.append("Apply robust scaling (RobustScaler) or winsorization.")
            recommendations.append("Investigate if these are legitimate extreme events or data entry errors.")
        elif columns_with_outliers:
            severity = Severity.MEDIUM
            warnings.append(f"{len(columns_with_outliers)} columns have noticeable statistical outliers.")
            recommendations.append(f"Inspect outliers in: {', '.join(columns_with_outliers[:5])}")

        evidence = " | ".join(warnings) if warnings else "No significant outliers detected."
        explanation = "Statistical outliers may be valid data points. Distinguish between 'bad data' (errors) and genuine extremes before removing them."

        return OutlierFindings(
            columns_with_outliers=columns_with_outliers,
            total_outlier_rows=total_outlier_rows,
            outlier_fraction=outlier_fraction,
            severity=severity,
            evidence=evidence,
            explanation=explanation,
            recommendations=recommendations
        )
