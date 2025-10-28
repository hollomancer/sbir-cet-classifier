"""Integration tests for A/B testing framework and classification accuracy."""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from sbir_cet_classifier.evaluation.ab_testing import (
    ClassificationABTester,
    SolicitationEnhancementTester,
    ABTestResults,
)


class TestClassificationABTester:
    """Test A/B testing framework for classification improvements."""

    @pytest.fixture
    def ab_tester(self):
        """Create A/B tester."""
        return ClassificationABTester(confidence_level=0.95)

    @pytest.fixture
    def sample_predictions(self):
        """Create sample prediction data."""
        return {
            "baseline": ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"],
            "enhanced": ["A", "A", "A", "B", "A", "B", "A", "A", "A", "B"],
            "true_labels": ["A", "A", "A", "B", "A", "B", "A", "A", "A", "B"],
        }

    def test_ab_tester_initialization(self, ab_tester):
        """Test A/B tester initialization."""
        assert ab_tester.confidence_level == 0.95
        assert abs(ab_tester.alpha - 0.05) < 1e-10

    def test_compare_classifiers_basic(self, ab_tester, sample_predictions):
        """Test basic classifier comparison."""
        results = ab_tester.compare_classifiers(
            baseline_predictions=sample_predictions["baseline"],
            enhanced_predictions=sample_predictions["enhanced"],
            true_labels=sample_predictions["true_labels"],
            test_name="Basic Test",
        )

        assert isinstance(results, ABTestResults)
        assert results.test_name == "Basic Test"
        assert 0.0 <= results.baseline_accuracy <= 1.0
        assert 0.0 <= results.enhanced_accuracy <= 1.0
        assert results.sample_size == 10
        assert 0.0 <= results.p_value <= 1.0
        assert isinstance(results.is_significant, (bool, type(results.is_significant)))

    def test_compare_classifiers_improvement(self, ab_tester):
        """Test classifier comparison with clear improvement."""
        # Enhanced classifier is clearly better
        baseline_preds = ["A", "A", "B", "B", "A", "A", "B", "B", "A", "A"]
        enhanced_preds = ["A", "B", "B", "A", "A", "B", "B", "A", "A", "B"]
        true_labels = ["A", "B", "B", "A", "A", "B", "B", "A", "A", "B"]

        results = ab_tester.compare_classifiers(
            baseline_predictions=baseline_preds,
            enhanced_predictions=enhanced_preds,
            true_labels=true_labels,
        )

        assert results.enhanced_accuracy > results.baseline_accuracy
        assert results.improvement > 0

    def test_compare_classifiers_no_difference(self, ab_tester):
        """Test classifier comparison with no difference."""
        # Both classifiers perform identically
        predictions = ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"]
        true_labels = ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"]

        results = ab_tester.compare_classifiers(
            baseline_predictions=predictions,
            enhanced_predictions=predictions,
            true_labels=true_labels,
        )

        assert results.baseline_accuracy == results.enhanced_accuracy
        assert results.improvement == 0.0
        assert results.p_value == 1.0  # No difference

    def test_compare_classifiers_mismatched_lengths(self, ab_tester):
        """Test error handling for mismatched prediction lengths."""
        with pytest.raises(ValueError) as exc_info:
            ab_tester.compare_classifiers(
                baseline_predictions=["A", "B"],
                enhanced_predictions=["A", "B", "A"],
                true_labels=["A", "B"],
            )

        assert "same length" in str(exc_info.value)

    def test_mcnemar_test_calculation(self, ab_tester):
        """Test McNemar's test calculation."""
        baseline_preds = ["A", "A", "B", "B", "A"]
        enhanced_preds = ["A", "B", "B", "A", "A"]
        true_labels = ["A", "B", "B", "A", "A"]

        p_value = ab_tester._mcnemar_test(baseline_preds, enhanced_preds, true_labels)

        assert isinstance(p_value, float)
        assert 0.0 <= p_value <= 1.0

    def test_mcnemar_test_no_discordant_pairs(self, ab_tester):
        """Test McNemar's test with no discordant pairs."""
        # Both classifiers make identical predictions
        predictions = ["A", "B", "A", "B"]
        true_labels = ["A", "B", "A", "B"]

        p_value = ab_tester._mcnemar_test(predictions, predictions, true_labels)

        assert p_value == 1.0  # No difference

    def test_detailed_metrics_calculation(self, ab_tester, sample_predictions):
        """Test detailed metrics calculation."""
        results = ab_tester.compare_classifiers(
            baseline_predictions=sample_predictions["baseline"],
            enhanced_predictions=sample_predictions["enhanced"],
            true_labels=sample_predictions["true_labels"],
        )

        detailed = results.detailed_metrics

        assert "baseline_metrics" in detailed
        assert "enhanced_metrics" in detailed
        assert "improvements" in detailed
        assert "per_class_metrics" in detailed
        assert "confusion_matrices" in detailed

        # Check metric structure
        for metrics in [detailed["baseline_metrics"], detailed["enhanced_metrics"]]:
            assert "precision" in metrics
            assert "recall" in metrics
            assert "f1" in metrics

    def test_power_analysis(self, ab_tester):
        """Test power analysis for sample size calculation."""
        sample_size = ab_tester.power_analysis(effect_size=0.1, alpha=0.05, power=0.8)

        assert isinstance(sample_size, int)
        assert sample_size > 0

    def test_multiple_comparison_correction_bonferroni(self, ab_tester):
        """Test Bonferroni multiple comparison correction."""
        p_values = [0.01, 0.02, 0.03, 0.04, 0.05]

        corrected = ab_tester.multiple_comparison_correction(p_values, method="bonferroni")

        assert len(corrected) == len(p_values)
        assert all(corrected[i] >= p_values[i] for i in range(len(p_values)))
        assert all(p <= 1.0 for p in corrected)

    def test_multiple_comparison_correction_holm(self, ab_tester):
        """Test Holm-Bonferroni multiple comparison correction."""
        p_values = [0.01, 0.02, 0.03, 0.04, 0.05]

        corrected = ab_tester.multiple_comparison_correction(p_values, method="holm")

        assert len(corrected) == len(p_values)
        assert all(p <= 1.0 for p in corrected)

    def test_multiple_comparison_unknown_method(self, ab_tester):
        """Test error handling for unknown correction method."""
        with pytest.raises(ValueError) as exc_info:
            ab_tester.multiple_comparison_correction([0.01, 0.02], method="unknown")

        assert "Unknown correction method" in str(exc_info.value)

    def test_ab_test_results_to_dict(self, ab_tester, sample_predictions):
        """Test ABTestResults to_dict conversion."""
        results = ab_tester.compare_classifiers(
            baseline_predictions=sample_predictions["baseline"],
            enhanced_predictions=sample_predictions["enhanced"],
            true_labels=sample_predictions["true_labels"],
        )

        result_dict = results.to_dict()

        assert isinstance(result_dict, dict)
        assert "test_name" in result_dict
        assert "baseline_accuracy" in result_dict
        assert "enhanced_accuracy" in result_dict
        assert "improvement" in result_dict
        assert "p_value" in result_dict
        assert "is_significant" in result_dict
        assert "timestamp" in result_dict


class TestSolicitationEnhancementTester:
    """Test solicitation enhancement specific A/B testing."""

    @pytest.fixture
    def enhancement_tester(self):
        """Create solicitation enhancement tester."""
        return SolicitationEnhancementTester(confidence_level=0.95)

    @pytest.fixture
    def mock_classifiers(self):
        """Create mock classifiers."""
        baseline = Mock()
        baseline.predict.return_value = ["quantum_computing", "artificial_intelligence"]

        enhanced = Mock()
        enhanced.predict.return_value = ["quantum_computing", "artificial_intelligence"]

        return {"baseline": baseline, "enhanced": enhanced}

    @pytest.fixture
    def sample_awards(self):
        """Create sample award data."""
        return [
            {
                "award_id": "AWARD-001",
                "abstract": "Quantum computing research",
                "keywords": "quantum, computing",
                "solicitation_id": "SOL-001",
            },
            {
                "award_id": "AWARD-002",
                "abstract": "AI research project",
                "keywords": "artificial intelligence, ML",
                "solicitation_id": "SOL-002",
            },
        ]

    @pytest.fixture
    def sample_solicitation_data(self):
        """Create sample solicitation data."""
        return {
            "SOL-001": {
                "full_text": "Advanced quantum computing algorithms for cryptographic applications"
            },
            "SOL-002": {"full_text": "Machine learning systems for autonomous decision making"},
        }

    def test_enhancement_tester_initialization(self, enhancement_tester):
        """Test enhancement tester initialization."""
        assert hasattr(enhancement_tester, "ab_tester")
        assert enhancement_tester.ab_tester.confidence_level == 0.95

    def test_solicitation_enhancement_test(
        self, enhancement_tester, mock_classifiers, sample_awards, sample_solicitation_data
    ):
        """Test solicitation enhancement impact testing."""
        true_labels = ["quantum_computing", "artificial_intelligence"]

        results = enhancement_tester.test_solicitation_enhancement(
            baseline_classifier=mock_classifiers["baseline"],
            enhanced_classifier=mock_classifiers["enhanced"],
            test_awards=sample_awards,
            true_labels=true_labels,
            solicitation_data=sample_solicitation_data,
        )

        assert isinstance(results, ABTestResults)
        assert results.test_name == "Solicitation Enhancement Impact"
        assert results.sample_size == 2

    def test_category_wise_analysis(self, enhancement_tester):
        """Test category-wise improvement analysis."""
        # Create mock results with per-class metrics
        mock_results = ABTestResults(
            test_name="Test",
            baseline_accuracy=0.8,
            enhanced_accuracy=0.9,
            improvement=0.1,
            p_value=0.01,
            is_significant=True,
            confidence_level=0.95,
            sample_size=100,
            baseline_predictions=[],
            enhanced_predictions=[],
            true_labels=[],
            detailed_metrics={
                "per_class_metrics": {
                    "quantum_computing": {"baseline": {"f1": 0.7}, "enhanced": {"f1": 0.8}},
                    "artificial_intelligence": {"baseline": {"f1": 0.6}, "enhanced": {"f1": 0.75}},
                }
            },
        )

        analysis = enhancement_tester.category_wise_analysis(mock_results)

        assert isinstance(analysis, dict)
        assert "quantum_computing" in analysis
        assert "artificial_intelligence" in analysis

        for category, metrics in analysis.items():
            assert "baseline_f1" in metrics
            assert "enhanced_f1" in metrics
            assert "improvement" in metrics
            assert "relative_improvement" in metrics

    def test_generate_report(self, enhancement_tester):
        """Test comprehensive report generation."""
        # Create mock results
        mock_results = ABTestResults(
            test_name="Solicitation Enhancement Test",
            baseline_accuracy=0.75,
            enhanced_accuracy=0.85,
            improvement=0.10,
            p_value=0.001,
            is_significant=True,
            confidence_level=0.95,
            sample_size=1000,
            baseline_predictions=[],
            enhanced_predictions=[],
            true_labels=[],
            detailed_metrics={
                "baseline_metrics": {"precision": 0.74, "recall": 0.75, "f1": 0.745},
                "enhanced_metrics": {"precision": 0.84, "recall": 0.85, "f1": 0.845},
                "improvements": {"precision": 0.10, "recall": 0.10, "f1": 0.10},
                "per_class_metrics": {
                    "quantum_computing": {"baseline": {"f1": 0.7}, "enhanced": {"f1": 0.8}}
                },
            },
        )

        report = enhancement_tester.generate_report(mock_results)

        assert isinstance(report, str)
        assert "A/B Test Report" in report
        assert "Solicitation Enhancement Test" in report
        assert "Sample Size: 1000" in report
        assert "statistically significant" in report.lower()

    def test_save_results(self, enhancement_tester, tmp_path):
        """Test saving test results to file."""
        mock_results = ABTestResults(
            test_name="Test",
            baseline_accuracy=0.8,
            enhanced_accuracy=0.9,
            improvement=0.1,
            p_value=0.01,
            is_significant=True,
            confidence_level=0.95,
            sample_size=100,
            baseline_predictions=[],
            enhanced_predictions=[],
            true_labels=[],
            detailed_metrics={},
        )

        filepath = tmp_path / "test_results.json"
        enhancement_tester.save_results(mock_results, str(filepath))

        assert filepath.exists()

        # Verify file content
        import json

        with open(filepath) as f:
            data = json.load(f)

        assert data["test_name"] == "Test"
        assert data["baseline_accuracy"] == 0.8
        assert data["enhanced_accuracy"] == 0.9

    def test_enhancement_without_solicitation_data(
        self, enhancement_tester, mock_classifiers, sample_awards
    ):
        """Test enhancement testing without solicitation data."""
        true_labels = ["quantum_computing", "artificial_intelligence"]

        results = enhancement_tester.test_solicitation_enhancement(
            baseline_classifier=mock_classifiers["baseline"],
            enhanced_classifier=mock_classifiers["enhanced"],
            test_awards=sample_awards,
            true_labels=true_labels,
            solicitation_data=None,
        )

        assert isinstance(results, ABTestResults)
        assert results.sample_size == 2

    def test_statistical_significance_detection(self, enhancement_tester):
        """Test detection of statistical significance."""
        # Create data with clear improvement
        baseline_preds = ["A"] * 50 + ["B"] * 50  # 50% accuracy
        enhanced_preds = ["A"] * 80 + ["B"] * 20  # 80% accuracy
        true_labels = ["A"] * 100  # All should be A

        results = enhancement_tester.ab_tester.compare_classifiers(
            baseline_predictions=baseline_preds,
            enhanced_predictions=enhanced_preds,
            true_labels=true_labels,
        )

        assert results.enhanced_accuracy > results.baseline_accuracy
        assert results.improvement > 0
        # With such a large difference, should be significant
        assert results.p_value < 0.05

    def test_edge_case_perfect_classifiers(self, enhancement_tester):
        """Test edge case with perfect classifiers."""
        perfect_preds = ["A", "B", "A", "B", "A"]
        true_labels = ["A", "B", "A", "B", "A"]

        results = enhancement_tester.ab_tester.compare_classifiers(
            baseline_predictions=perfect_preds,
            enhanced_predictions=perfect_preds,
            true_labels=true_labels,
        )

        assert results.baseline_accuracy == 1.0
        assert results.enhanced_accuracy == 1.0
        assert results.improvement == 0.0
