"""
modelmedic.dataset_intelligence.duplicates
===========================================
Detects exact duplicate rows, duplicate columns, constant, and near-constant features.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import List

import pandas as pd

from .models import DuplicateFindings, Severity

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Detects duplicate rows, constant features, and duplicate columns."""

    def __init__(self, near_constant_threshold: float = 0.99) -> None:
        self.near_constant_threshold = near_constant_threshold

    def analyze(self, df: pd.DataFrame) -> DuplicateFindings:
        total_rows = len(df)
        if total_rows == 0:
            return DuplicateFindings(
                duplicate_rows=0,
                duplicate_row_ratio=0.0,
                duplicate_columns=[],
                constant_columns=[],
                near_constant_columns=[],
                severity=Severity.INFO,
                evidence="Dataset is empty.",
                explanation="No duplicates could be evaluated.",
                recommendations=[]
            )

        # Duplicate Rows
        duplicate_rows = int(df.duplicated().sum())
        duplicate_ratio = duplicate_rows / total_rows

        # Constant & Near Constant Columns
        constant_columns = []
        near_constant_columns = []
        
        for col in df.columns:
            counts = df[col].value_counts(dropna=False)
            if len(counts) == 0:
                continue
            
            top_freq = counts.iloc[0]
            if top_freq == total_rows:
                constant_columns.append(col)
            elif (top_freq / total_rows) >= self.near_constant_threshold:
                near_constant_columns.append(col)

        # Duplicate Columns (efficient heuristic)
        # Group by hash of the first 100 values to reduce search space
        sample_df = df.head(100)
        col_hashes = defaultdict(list)
        for col in df.columns:
            try:
                # use string representation hash for simple grouping
                col_hash = hash(tuple(sample_df[col].astype(str)))
                col_hashes[col_hash].append(col)
            except Exception:
                pass

        duplicate_columns = []
        for hash_val, cols in col_hashes.items():
            if len(cols) > 1:
                # Strict check
                for i in range(len(cols)):
                    for j in range(i + 1, len(cols)):
                        col1 = cols[i]
                        col2 = cols[j]
                        if col1 not in duplicate_columns and col2 not in duplicate_columns:
                            try:
                                if df[col1].equals(df[col2]):
                                    duplicate_columns.append(col2)
                            except Exception:
                                pass
        
        duplicate_columns = list(set(duplicate_columns))

        # Determine severity and recommendations
        severity = Severity.INFO
        recommendations = []
        warnings = []

        if duplicate_ratio > 0.20:
            severity = Severity.CRITICAL
            warnings.append(f"CRITICAL: {duplicate_ratio:.1%} of rows are exact duplicates.")
            recommendations.append("Investigate data collection. Consider deduplication if these are not expected repeated measurements.")
        elif duplicate_ratio > 0.05:
            severity = max(severity, Severity.HIGH)
            warnings.append(f"HIGH: {duplicate_ratio:.1%} of rows are duplicates.")
            recommendations.append("Remove duplicate rows before training unless the data implies a valid class prior.")
        elif duplicate_rows > 0:
            severity = max(severity, Severity.LOW)
            warnings.append(f"{duplicate_rows} exact duplicate rows found.")
        
        if constant_columns:
            severity = max(severity, Severity.MEDIUM)
            warnings.append(f"{len(constant_columns)} constant columns found.")
            recommendations.append(f"Drop constant columns: {', '.join(constant_columns[:5])}")

        if duplicate_columns:
            severity = max(severity, Severity.MEDIUM)
            warnings.append(f"{len(duplicate_columns)} duplicate columns found.")
            recommendations.append(f"Drop duplicate columns to avoid collinearity: {', '.join(duplicate_columns[:5])}")

        evidence = " | ".join(warnings) if warnings else "No severe duplicates or constants found."

        return DuplicateFindings(
            duplicate_rows=duplicate_rows,
            duplicate_row_ratio=duplicate_ratio,
            duplicate_columns=duplicate_columns,
            constant_columns=constant_columns,
            near_constant_columns=near_constant_columns,
            severity=severity,
            evidence=evidence,
            explanation="Duplicate rows can inflate evaluation metrics. Constant and duplicate columns provide no signal and can harm model stability.",
            recommendations=recommendations
        )
