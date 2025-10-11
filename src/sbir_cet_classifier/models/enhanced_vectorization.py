"""Solicitation-enhanced TF-IDF vectorization."""

import re
from typing import List, Dict, Tuple, Optional, Set
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import csr_matrix, hstack


class WeightedTextCombiner:
    """Combine multiple text sources with configurable weights."""
    
    def __init__(self, weights: Dict[str, float], normalize_weights: bool = False):
        """Initialize with text source weights."""
        self.weights = weights.copy()
        
        if normalize_weights:
            total_weight = sum(weights.values())
            if total_weight > 0:
                self.weights = {k: v / total_weight for k, v in weights.items()}
    
    def combine_texts(self, text_sources: Dict[str, str]) -> str:
        """Combine texts according to weights."""
        combined_parts = []
        
        for source, weight in self.weights.items():
            text = text_sources.get(source, "")
            if text and weight > 0:
                # Repeat text based on weight (simple approach)
                repetitions = max(1, int(weight * 10))  # Scale weight to repetitions
                combined_parts.extend([text] * repetitions)
        
        return " ".join(combined_parts)


class CETAwareTfidfVectorizer:
    """TF-IDF vectorizer with CET keyword boosting."""
    
    def __init__(self, cet_keywords_boost: float = 2.0,
                 technical_terms_boost: float = 1.5,
                 custom_cet_vocabulary: Optional[List[str]] = None,
                 **tfidf_params):
        """Initialize with CET-aware parameters."""
        if cet_keywords_boost <= 1.0:
            raise ValueError("CET keywords boost must be > 1.0")
        if technical_terms_boost < 1.0:
            raise ValueError("Technical terms boost must be >= 1.0")
        
        self.cet_keywords_boost = cet_keywords_boost
        self.technical_terms_boost = technical_terms_boost
        self.custom_cet_vocabulary = custom_cet_vocabulary or []
        
        # Initialize base vectorizer
        self.vectorizer = TfidfVectorizer(**tfidf_params)
        
        # CET keyword mappings
        self.cet_keywords_map = {
            "quantum": ["quantum", "qubit", "superposition", "entanglement"],
            "artificial": ["artificial", "ai", "machine learning", "neural", "deep learning"],
            "nanotechnology": ["nano", "nanotechnology", "nanoscale", "nanoparticles"],
            "cybersecurity": ["cyber", "cybersecurity", "encryption", "cryptography"],
            "biotechnology": ["bio", "biotechnology", "bioengineering", "synthetic biology"],
            "materials": ["materials", "composites", "metamaterials", "advanced materials"],
            "autonomous": ["autonomous", "robotics", "unmanned", "self-driving"],
            "semiconductors": ["semiconductor", "microelectronics", "integrated circuit"]
        }
        
        # Technical terms
        self.technical_terms = {
            "algorithm", "protocol", "system", "framework", "architecture",
            "methodology", "technique", "approach", "solution", "platform",
            "interface", "network", "sensor", "device", "component", "software",
            "hardware", "application", "technology", "innovation"
        }
        
        self.is_fitted_ = False
    
    def fit(self, documents: List[str]):
        """Fit the vectorizer with CET awareness."""
        self.vectorizer.fit(documents)
        self.is_fitted_ = True
        return self
    
    def transform(self, documents: List[str]) -> csr_matrix:
        """Transform documents with CET keyword boosting."""
        if not self.is_fitted_:
            raise ValueError("Vectorizer must be fitted before transform")
        
        # Get base TF-IDF matrix
        tfidf_matrix = self.vectorizer.transform(documents)
        
        # Apply CET keyword boosting
        feature_names = self.vectorizer.get_feature_names_out()
        cet_keywords = self.get_cet_keywords()
        technical_terms = self.get_technical_terms()
        
        # Create boosting matrix
        boosted_matrix = tfidf_matrix.copy()
        
        for i, feature in enumerate(feature_names):
            if any(cet_keyword in feature.lower() for cet_keyword in cet_keywords):
                # Boost CET keywords
                boosted_matrix[:, i] *= self.cet_keywords_boost
            elif any(tech_term in feature.lower() for tech_term in technical_terms):
                # Boost technical terms
                boosted_matrix[:, i] *= self.technical_terms_boost
        
        return boosted_matrix
    
    def fit_transform(self, documents: List[str]) -> csr_matrix:
        """Fit and transform in one step."""
        return self.fit(documents).transform(documents)
    
    def get_feature_names_out(self) -> List[str]:
        """Get feature names."""
        if not self.is_fitted_:
            raise ValueError("Vectorizer must be fitted before getting feature names")
        return self.vectorizer.get_feature_names_out()
    
    def get_cet_keywords(self) -> Set[str]:
        """Get all CET-related keywords."""
        cet_keywords = set(self.custom_cet_vocabulary)
        
        for category, keywords in self.cet_keywords_map.items():
            cet_keywords.update(keywords)
        
        return cet_keywords
    
    def get_technical_terms(self) -> Set[str]:
        """Get technical terms."""
        return self.technical_terms.copy()
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance based on CET relevance."""
        if not self.is_fitted_:
            raise ValueError("Vectorizer must be fitted before getting feature importance")
        
        feature_names = self.get_feature_names_out()
        cet_keywords = self.get_cet_keywords()
        technical_terms = self.get_technical_terms()
        
        importance_scores = {}
        
        for feature in feature_names:
            score = 1.0  # Base score
            
            # Boost CET keywords
            if any(cet_keyword in feature.lower() for cet_keyword in cet_keywords):
                score *= self.cet_keywords_boost
            
            # Boost technical terms
            elif any(tech_term in feature.lower() for tech_term in technical_terms):
                score *= self.technical_terms_boost
            
            importance_scores[feature] = score
        
        return importance_scores


class SolicitationEnhancedTfidfVectorizer:
    """TF-IDF vectorizer enhanced with solicitation text integration."""
    
    def __init__(self, abstract_weight: float = 0.5,
                 keywords_weight: float = 0.2,
                 solicitation_weight: float = 0.3,
                 max_features: int = 10000,
                 ngram_range: Tuple[int, int] = (1, 2),
                 **tfidf_params):
        """Initialize enhanced vectorizer."""
        if abs(abstract_weight + keywords_weight + solicitation_weight - 1.0) > 1e-6:
            raise ValueError("Weights must sum to 1.0")
        
        self.abstract_weight = abstract_weight
        self.keywords_weight = keywords_weight
        self.solicitation_weight = solicitation_weight
        self.max_features = max_features
        self.ngram_range = ngram_range
        
        # Initialize individual vectorizers
        vectorizer_params = {
            'max_features': max_features // 3,  # Distribute features across sources
            'ngram_range': ngram_range,
            **tfidf_params
        }
        
        self.abstract_vectorizer = TfidfVectorizer(**vectorizer_params)
        self.keywords_vectorizer = TfidfVectorizer(**vectorizer_params)
        self.solicitation_vectorizer = TfidfVectorizer(**vectorizer_params)
        
        self.is_fitted_ = False
        self.feature_names_ = []
        self.vocabulary_ = {}
    
    def fit(self, documents: List[Dict[str, str]]):
        """Fit vectorizers on document sources."""
        abstracts = [doc.get("abstract", "") for doc in documents]
        keywords = [doc.get("keywords", "") for doc in documents]
        solicitations = [doc.get("solicitation_text", "") for doc in documents]
        
        # Fit individual vectorizers
        self.abstract_vectorizer.fit(abstracts)
        self.keywords_vectorizer.fit(keywords)
        self.solicitation_vectorizer.fit(solicitations)
        
        # Build combined feature names and vocabulary
        self._build_combined_vocabulary()
        
        self.is_fitted_ = True
        return self
    
    def transform(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Transform documents to weighted feature matrix."""
        if not self.is_fitted_:
            raise ValueError("Vectorizer must be fitted before transform")
        
        abstracts = [doc.get("abstract", "") for doc in documents]
        keywords = [doc.get("keywords", "") for doc in documents]
        solicitations = [doc.get("solicitation_text", "") for doc in documents]
        
        # Transform each source
        abstract_features = self.abstract_vectorizer.transform(abstracts)
        keywords_features = self.keywords_vectorizer.transform(keywords)
        solicitation_features = self.solicitation_vectorizer.transform(solicitations)
        
        # Apply weights
        abstract_features = abstract_features * self.abstract_weight
        keywords_features = keywords_features * self.keywords_weight
        solicitation_features = solicitation_features * self.solicitation_weight
        
        # Combine horizontally
        combined_features = hstack([abstract_features, keywords_features, solicitation_features])
        
        return combined_features
    
    def fit_transform(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Fit and transform in one step."""
        return self.fit(documents).transform(documents)
    
    def get_feature_names_out(self) -> List[str]:
        """Get combined feature names."""
        if not self.is_fitted_:
            raise ValueError("Vectorizer must be fitted before getting feature names")
        return self.feature_names_
    
    def _build_combined_vocabulary(self):
        """Build combined vocabulary and feature names."""
        # Get feature names from each vectorizer
        abstract_features = [f"abstract_{name}" for name in self.abstract_vectorizer.get_feature_names_out()]
        keywords_features = [f"keywords_{name}" for name in self.keywords_vectorizer.get_feature_names_out()]
        solicitation_features = [f"solicitation_{name}" for name in self.solicitation_vectorizer.get_feature_names_out()]
        
        # Combine all feature names
        self.feature_names_ = abstract_features + keywords_features + solicitation_features
        
        # Build vocabulary mapping
        self.vocabulary_ = {name: i for i, name in enumerate(self.feature_names_)}
        
        # Limit to max_features if specified
        if len(self.feature_names_) > self.max_features:
            self.feature_names_ = self.feature_names_[:self.max_features]
            self.vocabulary_ = {name: i for i, name in enumerate(self.feature_names_)}
    
    def _get_abstract_features(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Get abstract features (for testing)."""
        abstracts = [doc.get("abstract", "") for doc in documents]
        return self.abstract_vectorizer.transform(abstracts)
    
    def _get_keywords_features(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Get keywords features (for testing)."""
        keywords = [doc.get("keywords", "") for doc in documents]
        return self.keywords_vectorizer.transform(keywords)
    
    def _get_solicitation_features(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Get solicitation features (for testing)."""
        solicitations = [doc.get("solicitation_text", "") for doc in documents]
        return self.solicitation_vectorizer.transform(solicitations)
