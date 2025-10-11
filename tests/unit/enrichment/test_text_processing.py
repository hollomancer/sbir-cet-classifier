"""Tests for solicitation text parsing and keyword extraction."""

import pytest
from unittest.mock import Mock, patch

from src.sbir_cet_classifier.data.enrichment.text_processing import (
    SolicitationTextProcessor,
    TechnicalKeywordExtractor,
    CETRelevanceScorer
)


class TestSolicitationTextProcessor:
    """Test SolicitationTextProcessor."""

    @pytest.fixture
    def processor(self):
        """Create text processor."""
        return SolicitationTextProcessor()

    def test_extract_technical_requirements(self, processor):
        """Test extraction of technical requirements section."""
        full_text = """
        SOLICITATION OVERVIEW
        This is the overview section.
        
        TECHNICAL REQUIREMENTS
        The technical approach must demonstrate:
        1. Advanced quantum algorithms
        2. Machine learning integration
        3. Cybersecurity protocols
        
        EVALUATION CRITERIA
        Proposals will be evaluated on technical merit.
        """
        
        requirements = processor.extract_technical_requirements(full_text)
        
        assert "quantum algorithms" in requirements
        assert "machine learning integration" in requirements
        assert "cybersecurity protocols" in requirements
        assert "EVALUATION CRITERIA" not in requirements

    def test_extract_evaluation_criteria(self, processor):
        """Test extraction of evaluation criteria section."""
        full_text = """
        TECHNICAL REQUIREMENTS
        Technical requirements here.
        
        EVALUATION CRITERIA
        Proposals will be evaluated based on:
        - Technical innovation (40%)
        - Commercial potential (30%)
        - Team qualifications (30%)
        
        SUBMISSION REQUIREMENTS
        Submit by deadline.
        """
        
        criteria = processor.extract_evaluation_criteria(full_text)
        
        assert "Technical innovation" in criteria
        assert "Commercial potential" in criteria
        assert "Team qualifications" in criteria
        assert "SUBMISSION REQUIREMENTS" not in criteria

    def test_clean_text(self, processor):
        """Test text cleaning functionality."""
        dirty_text = """
        This   has    multiple    spaces.
        
        
        And multiple newlines.
        
        Also has <html>tags</html> and special chars: @#$%
        """
        
        clean_text = processor.clean_text(dirty_text)
        
        assert "multiple    spaces" not in clean_text
        assert "\n\n\n" not in clean_text
        assert "<html>" not in clean_text
        assert "tags" in clean_text  # Content should remain

    def test_extract_funding_information(self, processor):
        """Test extraction of funding information."""
        full_text = """
        FUNDING INFORMATION
        Phase I awards: $100,000 - $300,000
        Phase II awards: $500,000 - $1,000,000
        Performance period: 12 months for Phase I, 24 months for Phase II
        """
        
        funding_info = processor.extract_funding_information(full_text)
        
        assert funding_info["phase_i_min"] == 100000
        assert funding_info["phase_i_max"] == 300000
        assert funding_info["phase_ii_min"] == 500000
        assert funding_info["phase_ii_max"] == 1000000

    def test_extract_deadlines(self, processor):
        """Test extraction of proposal deadlines."""
        full_text = """
        IMPORTANT DATES
        Proposal submission deadline: June 15, 2024
        Award notification: September 1, 2024
        Performance start date: October 1, 2024
        """
        
        deadlines = processor.extract_deadlines(full_text)
        
        assert "2024-06-15" in str(deadlines["proposal_deadline"])
        assert "2024-09-01" in str(deadlines["award_notification"])
        assert "2024-10-01" in str(deadlines["performance_start"])


class TestTechnicalKeywordExtractor:
    """Test TechnicalKeywordExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create keyword extractor."""
        return TechnicalKeywordExtractor()

    def test_extract_cet_keywords(self, extractor):
        """Test extraction of CET-related keywords."""
        text = """
        This project focuses on quantum computing applications in artificial intelligence.
        We will develop machine learning algorithms using advanced materials and
        nanotechnology. The system will incorporate cybersecurity protocols and
        biotechnology sensors for autonomous systems.
        """
        
        keywords = extractor.extract_cet_keywords(text)
        
        expected_keywords = [
            "quantum computing", "artificial intelligence", "machine learning",
            "advanced materials", "nanotechnology", "cybersecurity", 
            "biotechnology", "autonomous systems"
        ]
        
        for keyword in expected_keywords:
            assert keyword in keywords

    def test_extract_technical_phrases(self, extractor):
        """Test extraction of technical phrases."""
        text = """
        The research will investigate deep neural networks, convolutional architectures,
        and reinforcement learning algorithms. We will use semiconductor fabrication
        techniques and quantum error correction methods.
        """
        
        phrases = extractor.extract_technical_phrases(text)
        
        assert "deep neural networks" in phrases
        assert "convolutional architectures" in phrases
        assert "reinforcement learning" in phrases
        assert "semiconductor fabrication" in phrases
        assert "quantum error correction" in phrases

    def test_filter_domain_specific_terms(self, extractor):
        """Test filtering of domain-specific technical terms."""
        all_terms = [
            "machine learning", "data analysis", "project management",
            "quantum computing", "team collaboration", "advanced materials",
            "budget planning", "nanotechnology"
        ]
        
        technical_terms = extractor.filter_domain_specific_terms(all_terms)
        
        # Should keep technical terms
        assert "machine learning" in technical_terms
        assert "quantum computing" in technical_terms
        assert "advanced materials" in technical_terms
        assert "nanotechnology" in technical_terms
        
        # Should filter out non-technical terms
        assert "project management" not in technical_terms
        assert "team collaboration" not in technical_terms
        assert "budget planning" not in technical_terms

    def test_rank_keywords_by_relevance(self, extractor):
        """Test ranking keywords by CET relevance."""
        keywords = [
            "quantum computing", "project timeline", "artificial intelligence",
            "budget allocation", "cybersecurity", "team meetings"
        ]
        
        ranked_keywords = extractor.rank_keywords_by_relevance(keywords)
        
        # Technical keywords should rank higher
        assert ranked_keywords.index("quantum computing") < ranked_keywords.index("project timeline")
        assert ranked_keywords.index("artificial intelligence") < ranked_keywords.index("budget allocation")
        assert ranked_keywords.index("cybersecurity") < ranked_keywords.index("team meetings")


class TestCETRelevanceScorer:
    """Test CETRelevanceScorer."""

    @pytest.fixture
    def scorer(self):
        """Create CET relevance scorer."""
        return CETRelevanceScorer()

    def test_calculate_relevance_scores(self, scorer):
        """Test calculation of CET relevance scores."""
        text = """
        This quantum computing research project will develop artificial intelligence
        algorithms for cybersecurity applications. The work involves advanced materials
        research and nanotechnology fabrication techniques.
        """
        
        scores = scorer.calculate_relevance_scores(text)
        
        assert isinstance(scores, dict)
        assert len(scores) > 0
        
        # Should have high scores for mentioned technologies
        assert scores.get("quantum_computing", 0) > 0.7
        assert scores.get("artificial_intelligence", 0) > 0.7
        assert scores.get("cybersecurity", 0) > 0.7
        assert scores.get("advanced_materials", 0) > 0.7
        
        # Should have lower scores for unmentioned technologies
        assert scores.get("biotechnology", 0) < 0.3

    def test_score_individual_cet_category(self, scorer):
        """Test scoring for individual CET category."""
        quantum_text = """
        Quantum computing research focusing on quantum algorithms,
        quantum error correction, and quantum cryptography applications.
        """
        
        score = scorer.score_cet_category(quantum_text, "quantum_computing")
        
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # Should be highly relevant

    def test_normalize_scores(self, scorer):
        """Test score normalization."""
        raw_scores = {
            "quantum_computing": 0.95,
            "artificial_intelligence": 0.85,
            "cybersecurity": 0.75,
            "biotechnology": 0.15,
            "space_technology": 0.05
        }
        
        normalized_scores = scorer.normalize_scores(raw_scores)
        
        assert all(0.0 <= score <= 1.0 for score in normalized_scores.values())
        assert sum(normalized_scores.values()) <= 1.0
        
        # Relative ordering should be preserved
        assert (normalized_scores["quantum_computing"] > 
                normalized_scores["artificial_intelligence"])
        assert (normalized_scores["artificial_intelligence"] > 
                normalized_scores["cybersecurity"])

    def test_get_top_relevant_categories(self, scorer):
        """Test getting top relevant CET categories."""
        scores = {
            "quantum_computing": 0.95,
            "artificial_intelligence": 0.85,
            "cybersecurity": 0.75,
            "advanced_materials": 0.65,
            "biotechnology": 0.15,
            "space_technology": 0.05
        }
        
        top_categories = scorer.get_top_relevant_categories(scores, top_n=3)
        
        assert len(top_categories) == 3
        assert top_categories[0] == ("quantum_computing", 0.95)
        assert top_categories[1] == ("artificial_intelligence", 0.85)
        assert top_categories[2] == ("cybersecurity", 0.75)

    @patch('src.sbir_cet_classifier.data.enrichment.text_processing.spacy')
    def test_extract_entities_with_spacy(self, mock_spacy, scorer):
        """Test entity extraction using spaCy."""
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_ent = Mock()
        mock_ent.text = "quantum computing"
        mock_ent.label_ = "TECHNOLOGY"
        mock_doc.ents = [mock_ent]
        mock_nlp.return_value = mock_doc
        mock_spacy.load.return_value = mock_nlp
        
        text = "Research in quantum computing applications."
        entities = scorer.extract_entities(text)
        
        assert "quantum computing" in entities
        mock_nlp.assert_called_once_with(text)
