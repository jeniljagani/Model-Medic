"""
modelmedic.dataset_intelligence.analyzer
=========================================
Orchestrates all dataset intelligence modules and produces
the unified DatasetDiagnosisReport.
"""
from __future__ import annotations

import logging
from typing import Optional, Any

import pandas as pd

from .models import DatasetDiagnosisReport, OverallHealthScore, Severity
from .profiler import DatasetProfiler
from .missing_values import MissingValueDetector
from .duplicates import DuplicateDetector
from .class_balance import ClassBalanceAnalyzer
from .outliers import OutlierDetector
from .distributions import DistributionAnalyzer
from .correlation import CorrelationAnalyzer
from .multicollinearity import MulticollinearityAnalyzer
from .target import TargetAnalyzer
from .leakage import LeakageDetector

logger = logging.getLogger(__name__)


class DatasetAnalyzer:
    """Orchestrates dataset intelligence modules."""

    def __init__(self) -> None:
        self._profiler = DatasetProfiler()
        self._missing_detector = MissingValueDetector()
        self._duplicate_detector = DuplicateDetector()
        self._balance_analyzer = ClassBalanceAnalyzer()
        self._outlier_detector = OutlierDetector()
        self._distribution_analyzer = DistributionAnalyzer()
        self._correlation_analyzer = CorrelationAnalyzer()
        self._multicollinearity_analyzer = MulticollinearityAnalyzer()
        self._target_analyzer = TargetAnalyzer()
        self._leakage_detector = LeakageDetector()

    def analyze(
        self,
        df: pd.DataFrame,
        target_column: Optional[str] = None,
    ) -> DatasetDiagnosisReport:
        """Run all dataset analysis modules and compute the health score."""
        logger.info("Analyzing dataset: shape=%s", df.shape)
        
        # Base Profiling
        summary = self._profiler.profile_summary(df)
        score = 100
        deductions = []
        
        if df.empty:
            return DatasetDiagnosisReport(
                summary=summary,
                health_score=OverallHealthScore(score=0, deductions=[{"reason": "Dataset is empty", "points": 100}]),
                critical_issues=["Dataset contains 0 rows."]
            )
        
        # Independent Detectors
        missing_data = self._missing_detector.analyze(df)
        duplicates = self._duplicate_detector.analyze(df)
        outliers = self._outlier_detector.analyze(df)
        distributions = self._distribution_analyzer.analyze(df)
        correlations = self._correlation_analyzer.analyze(df)
        multicollinearity = self._multicollinearity_analyzer.analyze(df)
        
        # Target-aware Detectors
        target_analysis = None
        class_balance = None
        leakage = self._leakage_detector.analyze(df, target_column=target_column)

        if target_column:
            target_analysis = self._target_analyzer.analyze(df, target_column)
            if target_analysis.target_type == "classification":
                class_balance = self._balance_analyzer.analyze(df, target_column)

        # Build unified report and aggregate recommendations/warnings
        critical_issues = []
        warnings = []
        recommendations = []
        
        findings: list[Any] = [missing_data, duplicates, outliers, distributions, 
                    correlations, multicollinearity, leakage]
        if target_analysis:
            findings.append(target_analysis)
        if class_balance:
            findings.append(class_balance)

        for finding in findings:
            if finding.severity == Severity.CRITICAL:
                critical_issues.append(finding.evidence)
            elif finding.severity in (Severity.HIGH, Severity.MEDIUM):
                warnings.append(finding.evidence)
            elif finding.severity == Severity.LOW:
                # Low severity items can just be stored in the specific findings
                pass
            
            for rec in finding.recommendations:
                if rec not in recommendations:
                    recommendations.append(rec)

        health_score = self._compute_health_score(findings)

        return DatasetDiagnosisReport(
            summary=summary,
            health_score=health_score,
            missing_data=missing_data,
            duplicates=duplicates,
            class_balance=class_balance,
            outliers=outliers,
            distributions=distributions,
            correlations=correlations,
            multicollinearity=multicollinearity,
            target_analysis=target_analysis,
            leakage=leakage,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations,
        )

    def _compute_health_score(self, findings: list) -> OverallHealthScore:
        """Deterministically calculate dataset health out of 100 based on severities."""
        score = 100
        deductions = []
        
        for finding in findings:
            finding_type = finding.__class__.__name__.replace('Findings', '')
            deduction = 0
            if finding.severity == Severity.CRITICAL:
                deduction = 25
            elif finding.severity == Severity.HIGH:
                deduction = 15
            elif finding.severity == Severity.MEDIUM:
                deduction = 5
            elif finding.severity == Severity.LOW:
                deduction = 2
            
            if deduction > 0:
                score -= deduction
                deductions.append({
                    "reason": f"{finding_type}: {finding.severity.value.upper()}",
                    "points": deduction
                })
                
        score = max(0, score)
        return OverallHealthScore(score=score, deductions=deductions)

