from __future__ import annotations

import logging
import pandas as pd
from typing import List, Any, Optional

from .models import LeakageFindings, Severity

logger = logging.getLogger(__name__)


class LeakageDetector:
    """Detects heuristic signals for potential data leakage."""

    def __init__(self, high_correlation_leakage_threshold: float = 0.98) -> None:
        self.high_correlation_leakage_threshold = high_correlation_leakage_threshold

    def analyze(self, df: pd.DataFrame, target_column: Optional[str] = None) -> LeakageFindings:
        signals = []
        warnings = []
        recommendations = []

        total_rows = len(df)
        
        # 1. Identifier-like columns
        # Check for columns named 'id', 'uuid', 'index', etc.
        id_keywords = ["_id", "id_", "uuid", "guid", "index"]
        for col in df.columns:
            if col == target_column:
                continue
            col_lower = str(col).lower()
            if col_lower == "id" or any(k in col_lower for k in id_keywords):
                # Check if it actually behaves like an ID (high cardinality)
                if df[col].nunique() >= total_rows * 0.9:
                    signals.append({
                        "feature": col,
                        "signal": "Identifier-like column",
                        "confidence": "High"
                    })
                    warnings.append(f"Column '{col}' appears to be a unique identifier.")
                    recommendations.append(f"Drop identifier column '{col}' before training to prevent overfitting.")

        # 2. Suspiciously correlated with target
        if target_column and target_column in df.columns:
            numeric_cols = df.select_dtypes(include=[float, int, "number"]).columns
            if target_column in numeric_cols:
                target_series = df[target_column]
                
                for col in numeric_cols:
                    if col == target_column:
                        continue
                    
                    try:
                        # Quick Pearson correlation
                        corr = df[col].corr(target_series)
                        if pd.notna(corr) and abs(corr) >= self.high_correlation_leakage_threshold:
                            signals.append({
                                "feature": col,
                                "signal": f"Suspiciously high correlation with target (|r| = {abs(corr):.3f})",
                                "confidence": "Medium"
                            })
                            warnings.append(f"Column '{col}' is perfectly/highly correlated with target.")
                            recommendations.append(f"Investigate '{col}'. It may be a post-outcome variable representing data leakage.")
                    except Exception:
                        pass

        severity = Severity.INFO
        if any(s["confidence"] == "High" for s in signals):
            severity = Severity.HIGH
        elif signals:
            severity = Severity.MEDIUM

        evidence = " | ".join(warnings) if warnings else "No obvious leakage signals detected."
        explanation = "Data leakage occurs when information from outside the training dataset (or from the future) is used to create the model."

        return LeakageFindings(
            leakage_signals=signals,
            severity=severity,
            evidence=evidence,
            explanation=explanation,
            recommendations=recommendations
        )
