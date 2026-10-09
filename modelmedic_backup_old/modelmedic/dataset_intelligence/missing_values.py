"""
modelmedic.dataset_intelligence.missing_values
===============================================
Detects and analyzes missing values in a pandas DataFrame.
"""
from __future__ import annotations

import logging
from typing import List

import pandas as pd

from .models import MissingDataFindings, Severity

logger = logging.getLogger(__name__)


class MissingValueDetector:
    """Detects missing values and missingness patterns."""

    def __init__(
        self,
        high_missing_threshold: float = 0.30,
        critical_missing_threshold: float = 0.70,
    ) -> None:
        self.high_missing_threshold = high_missing_threshold
        self.critical_missing_threshold = critical_missing_threshold

    def analyze(self, df: pd.DataFrame) -> MissingDataFindings:
        total_cells = df.shape[0] * df.shape[1]
        if total_cells == 0:
            return MissingDataFindings(
                total_missing_cells=0,
                missing_ratio=0.0,
                high_missing_columns=[],
                completely_missing_columns=[],
                severity=Severity.INFO,
                evidence="Empty dataset.",
                explanation="No data available to analyze missingness.",
                recommendations=[]
            )

        missing_counts = df.isnull().sum()
        total_missing = int(missing_counts.sum())
        missing_ratio = total_missing / total_cells

        completely_missing_columns = []
        high_missing_columns = []
        
        for col in df.columns:
            n_missing = int(missing_counts[col])
            col_ratio = n_missing / max(len(df), 1)
            
            if col_ratio == 1.0:
                completely_missing_columns.append(col)
            elif col_ratio >= self.critical_missing_threshold:
                high_missing_columns.append(col)
            elif col_ratio >= self.high_missing_threshold:
                high_missing_columns.append(col)

        severity = Severity.INFO
        warnings = []
        recommendations = []

        if completely_missing_columns:
            severity = Severity.CRITICAL
            warnings.append(f"{len(completely_missing_columns)} completely missing columns.")
            recommendations.append(f"Remove completely missing columns: {', '.join(completely_missing_columns[:5])}")

        if high_missing_columns:
            severity = max(severity, Severity.HIGH)
            warnings.append(f"{len(high_missing_columns)} columns have >{self.high_missing_threshold*100:.0f}% missing values.")
            recommendations.append(f"Investigate high missingness in: {', '.join(high_missing_columns[:5])}")
            recommendations.append("Consider model-based imputation or removing these features entirely.")

        if missing_ratio > 0.10:
            severity = max(severity, Severity.MEDIUM)
            warnings.append(f"High overall missing rate: {missing_ratio:.1%}.")
            recommendations.append("Use iterative imputation (e.g., KNNImputer) or a missing indicator feature.")
        elif missing_ratio > 0:
            severity = max(severity, Severity.LOW)
            warnings.append(f"Low overall missing rate: {missing_ratio:.1%}.")
            recommendations.append("Median/Mode imputation is likely sufficient.")
            
        if total_missing == 0:
            evidence = "No missing data detected."
            explanation = "The dataset is fully populated."
        else:
            evidence = " | ".join(warnings)
            explanation = "Missing data can reduce model accuracy and requires imputation or removal."

        return MissingDataFindings(
            total_missing_cells=total_missing,
            missing_ratio=missing_ratio,
            high_missing_columns=high_missing_columns,
            completely_missing_columns=completely_missing_columns,
            severity=severity,
            evidence=evidence,
            explanation=explanation,
            recommendations=recommendations
        )
