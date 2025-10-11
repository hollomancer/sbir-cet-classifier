"""A/B testing framework for classification accuracy improvement."""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from scipy import stats
import json
from datetime import datetime


@dataclass
class ABTestResults:
    """Results from A/B testing comparison."""
    
    test_name: str
    baseline_accuracy: float
    enhanced_accuracy: float
    improvement: float
    p_value: float
    is_significant: bool
    confidence_level: float
    sample_size: int
    baseline_predictions: List[Any]
    enhanced_predictions: List[Any]
    true_labels: List[Any]
    detailed_metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary."""
        return {
            "test_name": self.test_name,
            "baseline_accuracy": self.baseline_accuracy,
            "enhanced_accuracy": self.enhanced_accuracy,
            "improvement": self.improvement,
            "p_value": self.p_value,
            "is_significant": self.is_significant,
            "confidence_level": self.confidence_level,
            "sample_size": self.sample_size,
            "detailed_metrics": self.detailed_metrics,
            "timestamp": datetime.now().isoformat()
        }


class ClassificationABTester:
    """A/B testing framework for classification improvements."""
    
    def __init__(self, confidence_level: float = 0.95):
        """Initialize A/B tester."""
        self.confidence_level = confidence_level
        self.alpha = 1 - confidence_level
    
    def compare_classifiers(self, 
                          baseline_predictions: List[Any],
                          enhanced_predictions: List[Any],
                          true_labels: List[Any],
                          test_name: str = "Classification Comparison") -> ABTestResults:
        """Compare two sets of predictions using statistical testing."""
        
        if len(baseline_predictions) != len(enhanced_predictions) != len(true_labels):
            raise ValueError("All prediction arrays must have the same length")
        
        # Calculate accuracies
        baseline_accuracy = accuracy_score(true_labels, baseline_predictions)
        enhanced_accuracy = accuracy_score(true_labels, enhanced_predictions)
        improvement = enhanced_accuracy - baseline_accuracy
        
        # Perform McNemar's test for paired predictions
        p_value = self._mcnemar_test(baseline_predictions, enhanced_predictions, true_labels)
        is_significant = p_value < self.alpha
        
        # Calculate detailed metrics
        detailed_metrics = self._calculate_detailed_metrics(
            baseline_predictions, enhanced_predictions, true_labels
        )
        
        return ABTestResults(
            test_name=test_name,
            baseline_accuracy=baseline_accuracy,
            enhanced_accuracy=enhanced_accuracy,
            improvement=improvement,
            p_value=p_value,
            is_significant=is_significant,
            confidence_level=self.confidence_level,
            sample_size=len(true_labels),
            baseline_predictions=baseline_predictions,
            enhanced_predictions=enhanced_predictions,
            true_labels=true_labels,
            detailed_metrics=detailed_metrics
        )
    
    def _mcnemar_test(self, baseline_preds: List[Any], enhanced_preds: List[Any], 
                     true_labels: List[Any]) -> float:
        """Perform McNemar's test for paired predictions."""
        # Create contingency table
        baseline_correct = np.array(baseline_preds) == np.array(true_labels)
        enhanced_correct = np.array(enhanced_preds) == np.array(true_labels)
        
        # McNemar's test contingency table
        # |           | Enhanced Correct | Enhanced Wrong |
        # |-----------|------------------|----------------|
        # | Base Correct |       a       |       b        |
        # | Base Wrong   |       c       |       d        |
        
        a = np.sum(baseline_correct & enhanced_correct)
        b = np.sum(baseline_correct & ~enhanced_correct)
        c = np.sum(~baseline_correct & enhanced_correct)
        d = np.sum(~baseline_correct & ~enhanced_correct)
        
        # McNemar's test statistic
        if b + c == 0:
            return 1.0  # No difference
        
        # Use continuity correction for small samples
        if b + c < 25:
            chi2_stat = (abs(b - c) - 1) ** 2 / (b + c)
        else:
            chi2_stat = (b - c) ** 2 / (b + c)
        
        # Calculate p-value
        p_value = 1 - stats.chi2.cdf(chi2_stat, df=1)
        
        return p_value
    
    def _calculate_detailed_metrics(self, baseline_preds: List[Any], 
                                  enhanced_preds: List[Any], 
                                  true_labels: List[Any]) -> Dict[str, Any]:
        """Calculate detailed performance metrics."""
        
        # Get unique labels
        unique_labels = sorted(list(set(true_labels)))
        
        # Calculate metrics for baseline
        baseline_precision, baseline_recall, baseline_f1, _ = precision_recall_fscore_support(
            true_labels, baseline_preds, average='weighted', zero_division=0
        )
        
        # Calculate metrics for enhanced
        enhanced_precision, enhanced_recall, enhanced_f1, _ = precision_recall_fscore_support(
            true_labels, enhanced_preds, average='weighted', zero_division=0
        )
        
        # Per-class metrics
        baseline_per_class = precision_recall_fscore_support(
            true_labels, baseline_preds, average=None, zero_division=0
        )
        enhanced_per_class = precision_recall_fscore_support(
            true_labels, enhanced_preds, average=None, zero_division=0
        )
        
        per_class_metrics = {}
        for i, label in enumerate(unique_labels):
            per_class_metrics[str(label)] = {
                "baseline": {
                    "precision": float(baseline_per_class[0][i]),
                    "recall": float(baseline_per_class[1][i]),
                    "f1": float(baseline_per_class[2][i])
                },
                "enhanced": {
                    "precision": float(enhanced_per_class[0][i]),
                    "recall": float(enhanced_per_class[1][i]),
                    "f1": float(enhanced_per_class[2][i])
                }
            }
        
        # Confusion matrices
        baseline_cm = confusion_matrix(true_labels, baseline_preds, labels=unique_labels)
        enhanced_cm = confusion_matrix(true_labels, enhanced_preds, labels=unique_labels)
        
        return {
            "baseline_metrics": {
                "precision": float(baseline_precision),
                "recall": float(baseline_recall),
                "f1": float(baseline_f1)
            },
            "enhanced_metrics": {
                "precision": float(enhanced_precision),
                "recall": float(enhanced_recall),
                "f1": float(enhanced_f1)
            },
            "improvements": {
                "precision": float(enhanced_precision - baseline_precision),
                "recall": float(enhanced_recall - baseline_recall),
                "f1": float(enhanced_f1 - baseline_f1)
            },
            "per_class_metrics": per_class_metrics,
            "confusion_matrices": {
                "baseline": baseline_cm.tolist(),
                "enhanced": enhanced_cm.tolist(),
                "labels": unique_labels
            }
        }
    
    def power_analysis(self, effect_size: float, alpha: float = 0.05, 
                      power: float = 0.8) -> int:
        """Calculate required sample size for given effect size and power."""
        # Simplified power analysis for paired proportions
        # This is an approximation - more sophisticated methods exist
        
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_beta = stats.norm.ppf(power)
        
        # Approximate sample size calculation
        n = ((z_alpha + z_beta) ** 2) / (effect_size ** 2)
        
        return int(np.ceil(n))
    
    def multiple_comparison_correction(self, p_values: List[float], 
                                    method: str = "bonferroni") -> List[float]:
        """Apply multiple comparison correction."""
        p_values = np.array(p_values)
        
        if method == "bonferroni":
            corrected = p_values * len(p_values)
            corrected = np.minimum(corrected, 1.0)
        elif method == "holm":
            # Holm-Bonferroni method
            sorted_indices = np.argsort(p_values)
            corrected = np.zeros_like(p_values)
            
            for i, idx in enumerate(sorted_indices):
                correction_factor = len(p_values) - i
                corrected[idx] = min(p_values[idx] * correction_factor, 1.0)
                
                # Ensure monotonicity
                if i > 0:
                    prev_idx = sorted_indices[i-1]
                    corrected[idx] = max(corrected[idx], corrected[prev_idx])
        else:
            raise ValueError(f"Unknown correction method: {method}")
        
        return corrected.tolist()


class SolicitationEnhancementTester:
    """Specialized A/B tester for solicitation enhancement evaluation."""
    
    def __init__(self, confidence_level: float = 0.95):
        """Initialize solicitation enhancement tester."""
        self.ab_tester = ClassificationABTester(confidence_level)
    
    def test_solicitation_enhancement(self, 
                                    baseline_classifier,
                                    enhanced_classifier,
                                    test_awards: List[Dict[str, Any]],
                                    true_labels: List[str],
                                    solicitation_data: Optional[Dict[str, Any]] = None) -> ABTestResults:
        """Test the impact of solicitation enhancement on classification."""
        
        # Get baseline predictions (without solicitation data)
        baseline_predictions = []
        for award in test_awards:
            # Remove solicitation data for baseline
            baseline_award = {k: v for k, v in award.items() if k != 'solicitation_text'}
            pred = baseline_classifier.predict([baseline_award])[0]
            baseline_predictions.append(pred)
        
        # Get enhanced predictions (with solicitation data)
        enhanced_predictions = []
        for award in test_awards:
            # Ensure solicitation data is included
            enhanced_award = award.copy()
            if solicitation_data and award.get('solicitation_id'):
                sol_id = award['solicitation_id']
                if sol_id in solicitation_data:
                    enhanced_award['solicitation_text'] = solicitation_data[sol_id].get('full_text', '')
            
            pred = enhanced_classifier.predict([enhanced_award])[0]
            enhanced_predictions.append(pred)
        
        return self.ab_tester.compare_classifiers(
            baseline_predictions,
            enhanced_predictions,
            true_labels,
            test_name="Solicitation Enhancement Impact"
        )
    
    def category_wise_analysis(self, results: ABTestResults) -> Dict[str, Dict[str, float]]:
        """Analyze improvement by CET category."""
        category_analysis = {}
        
        per_class_metrics = results.detailed_metrics.get("per_class_metrics", {})
        
        for category, metrics in per_class_metrics.items():
            baseline_f1 = metrics["baseline"]["f1"]
            enhanced_f1 = metrics["enhanced"]["f1"]
            improvement = enhanced_f1 - baseline_f1
            
            category_analysis[category] = {
                "baseline_f1": baseline_f1,
                "enhanced_f1": enhanced_f1,
                "improvement": improvement,
                "relative_improvement": improvement / baseline_f1 if baseline_f1 > 0 else 0.0
            }
        
        return category_analysis
    
    def generate_report(self, results: ABTestResults) -> str:
        """Generate a comprehensive test report."""
        report = []
        report.append(f"# A/B Test Report: {results.test_name}")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        report.append("## Summary")
        report.append(f"- Sample Size: {results.sample_size}")
        report.append(f"- Baseline Accuracy: {results.baseline_accuracy:.4f}")
        report.append(f"- Enhanced Accuracy: {results.enhanced_accuracy:.4f}")
        report.append(f"- Improvement: {results.improvement:.4f} ({results.improvement/results.baseline_accuracy*100:.2f}%)")
        report.append(f"- Statistical Significance: {'Yes' if results.is_significant else 'No'} (p={results.p_value:.4f})")
        report.append("")
        
        # Detailed metrics
        baseline_metrics = results.detailed_metrics["baseline_metrics"]
        enhanced_metrics = results.detailed_metrics["enhanced_metrics"]
        improvements = results.detailed_metrics["improvements"]
        
        report.append("## Detailed Metrics")
        report.append("| Metric | Baseline | Enhanced | Improvement |")
        report.append("|--------|----------|----------|-------------|")
        report.append(f"| Precision | {baseline_metrics['precision']:.4f} | {enhanced_metrics['precision']:.4f} | {improvements['precision']:.4f} |")
        report.append(f"| Recall | {baseline_metrics['recall']:.4f} | {enhanced_metrics['recall']:.4f} | {improvements['recall']:.4f} |")
        report.append(f"| F1-Score | {baseline_metrics['f1']:.4f} | {enhanced_metrics['f1']:.4f} | {improvements['f1']:.4f} |")
        report.append("")
        
        # Category-wise analysis
        category_analysis = self.category_wise_analysis(results)
        if category_analysis:
            report.append("## Category-wise Analysis")
            report.append("| Category | Baseline F1 | Enhanced F1 | Improvement | Relative Improvement |")
            report.append("|----------|-------------|-------------|-------------|---------------------|")
            
            for category, metrics in category_analysis.items():
                report.append(
                    f"| {category} | {metrics['baseline_f1']:.4f} | {metrics['enhanced_f1']:.4f} | "
                    f"{metrics['improvement']:.4f} | {metrics['relative_improvement']:.2%} |"
                )
            report.append("")
        
        # Statistical interpretation
        report.append("## Statistical Interpretation")
        if results.is_significant:
            report.append(f"The improvement is statistically significant at the {results.confidence_level:.0%} confidence level.")
            report.append("This suggests that the solicitation enhancement provides a meaningful improvement in classification accuracy.")
        else:
            report.append(f"The improvement is not statistically significant at the {results.confidence_level:.0%} confidence level.")
            report.append("This could indicate that either the improvement is due to chance, or a larger sample size is needed.")
        
        return "\n".join(report)
    
    def save_results(self, results: ABTestResults, filepath: str):
        """Save test results to file."""
        with open(filepath, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)
