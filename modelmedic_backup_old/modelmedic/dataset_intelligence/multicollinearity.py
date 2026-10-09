from __future__ import annotations

import logging
import pandas as pd
import numpy as np

from sklearn.linear_model import LinearRegression
from .models import MulticollinearityFindings, Severity

logger = logging.getLogger(__name__)

class MulticollinearityAnalyzer:
    """Analyzes multicollinearity using Variance Inflation Factor (VIF)."""

    def __init__(self, high_vif_threshold: float = 10.0) -> None:
        self.high_vif_threshold = high_vif_threshold

    def analyze(self, df: pd.DataFrame) -> MulticollinearityFindings:
        numeric_cols = df.select_dtypes(include=[float, int, "number"]).columns
        if len(numeric_cols) < 2:
            return MulticollinearityFindings(
                high_vif_features={},
                severity=Severity.INFO,
                evidence="Not enough numeric columns.",
                explanation="VIF requires at least 2 numeric columns.",
                recommendations=[]
            )

        # Drop NaNs for VIF calculation and sample if necessary
        df_clean = df[numeric_cols].dropna()
        if len(df_clean) < 10:
            return MulticollinearityFindings(
                high_vif_features={},
                severity=Severity.INFO,
                evidence="Not enough complete rows after dropping NaNs.",
                explanation="VIF requires valid numerical rows.",
                recommendations=[]
            )

        if len(df_clean) > 10000:
            logger.info("Sampling 10k rows for VIF analysis.")
            df_clean = df_clean.sample(n=10000, random_state=42)

        high_vif_features = {}
        warnings = []
        recommendations = []
        
        # Calculate VIF iteratively using LinearRegression
        model = LinearRegression()
        for col in numeric_cols:
            X = df_clean.drop(columns=[col])
            y = df_clean[col]
            
            # Skip if constant target
            if y.nunique() <= 1:
                continue
                
            try:
                model.fit(X, y)
                r2 = model.score(X, y)
                if r2 >= 1.0 or r2 >= 0.9999:
                    vif = float('inf')
                else:
                    vif = 1.0 / (1.0 - r2)
                
                if vif > self.high_vif_threshold:
                    high_vif_features[col] = float(vif)
            except Exception:
                pass

        severity = Severity.INFO
        if high_vif_features:
            severity = Severity.HIGH
            warnings.append(f"{len(high_vif_features)} features exhibit high multicollinearity (VIF > {self.high_vif_threshold}).")
            recommendations.append("Severe multicollinearity causes unstable model weights. Remove highly correlated features or use Ridge Regression / PCA.")
            
        evidence = " | ".join(warnings) if warnings else "No severe multicollinearity detected."
        explanation = "Multicollinearity occurs when independent variables are highly correlated with each other."

        return MulticollinearityFindings(
            high_vif_features=high_vif_features,
            severity=severity,
            evidence=evidence,
            explanation=explanation,
            recommendations=recommendations
        )
