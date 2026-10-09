"""
modelmedic.dataset_intelligence.models
=======================================
Strongly typed domain models for Dataset Intelligence diagnostic findings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def _rank(self) -> int:
        return {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}[self.value]

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self._rank() < other._rank()
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self._rank() > other._rank()
        return NotImplemented


@dataclass
class DatasetSummary:
    rows: int
    columns: int
    memory_usage_mb: float
    dtypes_summary: Dict[str, int]


@dataclass
class MissingDataFindings:
    total_missing_cells: int
    missing_ratio: float
    high_missing_columns: List[str]
    completely_missing_columns: List[str]
    severity: Severity
    evidence: str
    explanation: str
    recommendations: List[str]


@dataclass
class DuplicateFindings:
    duplicate_rows: int
    duplicate_row_ratio: float
    duplicate_columns: List[str]
    constant_columns: List[str]
    near_constant_columns: List[str]
    severity: Severity
    evidence: str
    explanation: str
    recommendations: List[str]


@dataclass
class ClassBalanceFindings:
    target_column: str
    task_type: str  # "binary" or "multiclass"
    class_counts: Dict[str, int]
    minority_class: str
    majority_class: str
    imbalance_ratio: float
    dominant_percentage: float
    severity: Severity
    evidence: str
    explanation: str
    recommendations: List[str]


@dataclass
class OutlierFindings:
    columns_with_outliers: List[str]
    total_outlier_rows: int
    outlier_fraction: float
    severity: Severity
    evidence: str
    explanation: str
    recommendations: List[str]


@dataclass
class DistributionFindings:
    skewed_columns: List[str]
    heavy_tail_columns: List[str]
    zero_variance_columns: List[str]
    severity: Severity
    evidence: str
    explanation: str
    recommendations: List[str]


@dataclass
class CorrelationFindings:
    highly_correlated_pairs: List[tuple[str, str, float]]
    severity: Severity
    evidence: str
    explanation: str
    recommendations: List[str]


@dataclass
class MulticollinearityFindings:
    high_vif_features: Dict[str, float]
    severity: Severity
    evidence: str
    explanation: str
    recommendations: List[str]


@dataclass
class TargetFindings:
    target_column: str
    target_type: str  # "classification" or "regression"
    statistics: Dict[str, Any]
    severity: Severity
    evidence: str
    explanation: str
    recommendations: List[str]


@dataclass
class LeakageFindings:
    leakage_signals: List[Dict[str, Any]]  # e.g. {"feature": "id", "signal": "identifier"}
    severity: Severity
    evidence: str
    explanation: str
    recommendations: List[str]


@dataclass
class OverallHealthScore:
    score: int  # 0 to 100
    deductions: List[Dict[str, Any]]  # [{"reason": "Missing data", "points": 18}]


@dataclass
class DatasetDiagnosisReport:
    """Unified dataset intelligence report."""
    summary: DatasetSummary
    health_score: OverallHealthScore
    
    missing_data: Optional[MissingDataFindings] = None
    duplicates: Optional[DuplicateFindings] = None
    class_balance: Optional[ClassBalanceFindings] = None
    outliers: Optional[OutlierFindings] = None
    distributions: Optional[DistributionFindings] = None
    correlations: Optional[CorrelationFindings] = None
    multicollinearity: Optional[MulticollinearityFindings] = None
    target_analysis: Optional[TargetFindings] = None
    leakage: Optional[LeakageFindings] = None

    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)

    def get_report_summary(self) -> str:
        lines = [
            "=" * 60,
            "  ModelMedic Advanced Dataset Intelligence Report",
            "=" * 60,
            f"  Shape         : {self.summary.rows} rows x {self.summary.columns} columns",
            f"  Health Score  : {self.health_score.score}/100",
            f"  Memory        : {self.summary.memory_usage_mb:.2f} MB",
            f"  Dtypes        : {self.summary.dtypes_summary}",
            ""
        ]

        if self.critical_issues:
            lines.append("  CRITICAL ISSUES:")
            for c in self.critical_issues:
                lines.append(f"    ! {c}")
            lines.append("")

        if self.warnings:
            lines.append("  WARNINGS:")
            for w in self.warnings:
                lines.append(f"    - {w}")
            lines.append("")

        if self.recommendations:
            lines.append("  RECOMMENDATIONS:")
            for r in self.recommendations:
                lines.append(f"    → {r}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)
