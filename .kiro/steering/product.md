# Product Overview

The SBIR CET Classifier is an automated classification system for SBIR (Small Business Innovation Research) awards against 20 Critical and Emerging Technology (CET) areas defined by the NSTC framework.

## Core Functionality

- **ML-based Classification**: Uses TF-IDF vectorization and calibrated logistic regression to score award applicability (0-100) against CET taxonomy
- **Portfolio Analytics**: Provides summary statistics, agency distribution analysis, and funding breakdowns by technology area
- **Data Export**: Supports CSV/JSON export with flexible filtering by fiscal year, CET areas, and classification bands
- **Evidence Extraction**: Generates up to 3 evidence statements per classification with source attribution and rationale

## Classification System

Awards receive applicability scores in three bands:
- **High (≥70)**: Strong alignment with CET area
- **Medium (40-69)**: Moderate alignment 
- **Low (<40)**: Weak alignment

The system processes award abstracts, keywords, and metadata to determine the primary CET area and supporting secondary areas.

## Target Users

Research analysts, program managers, and policy makers who need to understand SBIR portfolio alignment with critical technology priorities.