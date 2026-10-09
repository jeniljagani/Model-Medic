from __future__ import annotations

import logging
import pandas as pd
from .models import CorrelationFindings, Severity

logger = logging.getLogger(__name__)

class CorrelationAnalyzer:
    """Analyzes correlations between numerical features."""

    def __init__(self, high_correlation_threshold: float = 0.90) -> None:
        self.high_correlation_threshold = high_correlation_threshold

    def analyze(self, df: pd.DataFrame) -> CorrelationFindings:
        numeric_cols = df.select_dtypes(include=[float, int, "number"]).columns
        if len(numeric_cols) < 2:
            return CorrelationFindings(
                highly_correlated_pairs=[],
                severity=Severity.INFO,
                evidence="Not enough numeric columns.",
                explanation="Correlation requires at least 2 numeric columns.",
                recommendations=[]
            )

        # Sample for performance if dataset is large
        if len(df) > 100000:
            logger.info("Sampling 100k rows for correlation analysis.")
            df_sampled = df.sample(n=100000, random_state=42)
        else:
            df_sampled = df

        corr_matrix = df_sampled[numeric_cols].corr(method='pearson')
        
        highly_correlated_pairs = []
        warnings = []
        recommendations = []

        cols = corr_matrix.columns
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                col1 = cols[i]
                col2 = cols[j]
                val = corr_matrix.iloc[i, j]
                if pd.notna(val) and abs(val) >= self.high_correlation_threshold:
                    highly_correlated_pairs.append((col1, col2, float(val)))

        severity = Severity.INFO
        if highly_correlated_pairs:
            severity = Severity.MEDIUM
            warnings.append(f"{len(highly_correlated_pairs)} highly correlated feature pairs found (|r| >= {self.high_correlation_threshold}).")
            recommendations.append("Highly correlated features can cause multicollinearity in linear models. Consider dropping one from each pair, or using PCA/Regularization.")
            # Do not blindly recommend deletion, just warn

        evidence = " | ".join(warnings) if warnings else "No highly correlated pairs found."
        explanation = "High correlation between independent variables means they carry redundant information."

        return CorrelationFindings(
            highly_correlated_pairs=highly_correlated_pairs,
            severity=severity,
            evidence=evidence,
            explanation=explanation,
            recommendations=recommendations
        )
