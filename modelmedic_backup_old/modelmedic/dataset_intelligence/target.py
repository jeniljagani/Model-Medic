from __future__ import annotations

import logging
import pandas as pd
from typing import Dict, Any

from .models import TargetFindings, Severity

logger = logging.getLogger(__name__)

class TargetAnalyzer:
    """Analyzes classification or regression target properties."""

    def analyze(self, df: pd.DataFrame, target_column: str) -> TargetFindings:
        if target_column not in df.columns:
            return TargetFindings(
                target_column=target_column,
                target_type="unknown",
                statistics={},
                severity=Severity.INFO,
                evidence=f"Target column '{target_column}' not found.",
                explanation="Target analysis cannot proceed.",
                recommendations=[]
            )

        series = df[target_column].dropna()
        if len(series) == 0:
            return TargetFindings(
                target_column=target_column,
                target_type="unknown",
                statistics={},
                severity=Severity.INFO,
                evidence="Target column contains no valid data.",
                explanation="Target analysis cannot proceed.",
                recommendations=[]
            )

        warnings = []
        recommendations = []
        stats: Dict[str, Any] = {}

        is_numeric = pd.api.types.is_numeric_dtype(series)
        unique_count = series.nunique()

        if is_numeric and unique_count > 20:
            target_type = "regression"
            stats["mean"] = float(series.mean())
            stats["median"] = float(series.median())
            stats["std"] = float(series.std())
            stats["min"] = float(series.min())
            stats["max"] = float(series.max())
            stats["skew"] = float(series.skew())
            
            if abs(stats["skew"]) > 2.0:
                warnings.append(f"Target '{target_column}' is highly skewed (skew={stats['skew']:.2f}).")
                recommendations.append("Consider applying a log transformation to the target variable to normalize residuals.")
        else:
            target_type = "classification"
            stats["unique_classes"] = unique_count
            if unique_count > 50:
                warnings.append(f"Target has a very high number of classes ({unique_count}).")
                recommendations.append("Ensure you actually have a classification task and not a regression task with binned data. Consider grouping rare classes.")

        severity = Severity.INFO
        if warnings:
            severity = Severity.LOW

        evidence = " | ".join(warnings) if warnings else f"Target appears healthy for {target_type}."
        explanation = "Understanding the target distribution dictates the choice of loss function and evaluation metrics."

        return TargetFindings(
            target_column=target_column,
            target_type=target_type,
            statistics=stats,
            severity=severity,
            evidence=evidence,
            explanation=explanation,
            recommendations=recommendations
        )
