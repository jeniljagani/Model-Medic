from __future__ import annotations

import logging
import pandas as pd
from .models import ClassBalanceFindings, Severity

logger = logging.getLogger(__name__)

class ClassBalanceAnalyzer:
    """Analyzes class distributions and detects class imbalance."""

    def __init__(
        self,
        severe_imbalance_threshold: float = 10.0,
        moderate_imbalance_threshold: float = 3.0,
    ) -> None:
        self.severe_imbalance_threshold = severe_imbalance_threshold
        self.moderate_imbalance_threshold = moderate_imbalance_threshold

    def analyze(self, df: pd.DataFrame, target_column: str) -> ClassBalanceFindings:
        if target_column not in df.columns:
            return ClassBalanceFindings(
                target_column=target_column,
                task_type="unknown",
                class_counts={},
                minority_class="",
                majority_class="",
                imbalance_ratio=0.0,
                dominant_percentage=0.0,
                severity=Severity.INFO,
                evidence=f"Target column '{target_column}' not found.",
                explanation="Cannot evaluate class balance.",
                recommendations=[]
            )

        counts = df[target_column].value_counts(dropna=True)
        if len(counts) == 0:
             return ClassBalanceFindings(
                target_column=target_column,
                task_type="unknown",
                class_counts={},
                minority_class="",
                majority_class="",
                imbalance_ratio=0.0,
                dominant_percentage=0.0,
                severity=Severity.INFO,
                evidence="Target column has no valid values.",
                explanation="Cannot evaluate class balance.",
                recommendations=[]
            )           

        if pd.api.types.is_numeric_dtype(df[target_column]) and len(counts) > 20:
            # Looks like regression
            return ClassBalanceFindings(
                target_column=target_column,
                task_type="regression",
                class_counts={},
                minority_class="",
                majority_class="",
                imbalance_ratio=0.0,
                dominant_percentage=0.0,
                severity=Severity.INFO,
                evidence=f"Target '{target_column}' appears continuous.",
                explanation="Class balance does not apply to regression.",
                recommendations=[]
            )

        task_type = "binary" if len(counts) == 2 else "multiclass"
        class_counts = counts.to_dict()
        
        majority_class = str(counts.index[0])
        minority_class = str(counts.index[-1])
        majority_count = float(counts.iloc[0])
        minority_count = float(counts.iloc[-1])
        
        imbalance_ratio = float(majority_count / max(minority_count, 1.0))
        dominant_percentage = float(majority_count / max(counts.sum(), 1.0))

        severity = Severity.INFO
        warnings = []
        recommendations = []

        if imbalance_ratio >= self.severe_imbalance_threshold:
            severity = Severity.HIGH
            warnings.append(f"Severe imbalance: {imbalance_ratio:.1f}:1 ratio.")
            recommendations.append("Consider class weighting or resampling (e.g., SMOTE for training, undersampling majority).")
            recommendations.append("Ensure you use PR-AUC or F1-score rather than accuracy for evaluation.")
        elif imbalance_ratio >= self.moderate_imbalance_threshold:
            severity = Severity.MEDIUM
            warnings.append(f"Moderate imbalance: {imbalance_ratio:.1f}:1 ratio.")
            recommendations.append("Consider class weighting in your loss function.")
        else:
            warnings.append("Classes are relatively balanced.")

        evidence = " | ".join(warnings)
        explanation = "Class imbalance can cause models to bias heavily toward the majority class."

        return ClassBalanceFindings(
            target_column=target_column,
            task_type=task_type,
            class_counts={str(k): int(v) for k, v in class_counts.items()},
            minority_class=minority_class,
            majority_class=majority_class,
            imbalance_ratio=imbalance_ratio,
            dominant_percentage=dominant_percentage,
            severity=severity,
            evidence=evidence,
            explanation=explanation,
            recommendations=recommendations
        )
