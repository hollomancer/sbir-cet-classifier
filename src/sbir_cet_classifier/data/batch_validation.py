"""Batch validation utilities for high-performance ingestion."""

import pandas as pd
from datetime import datetime

from sbir_cet_classifier.data.agency_mapping import normalize_agency_name


def prevalidate_batch(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pre-validate DataFrame using vectorized pandas operations.
    
    Filters out obviously invalid records before expensive Pydantic validation.
    
    Args:
        df: DataFrame with canonical column names
        
    Returns:
        Tuple of (valid_df, invalid_df)
    """
    # Create validation mask
    valid_mask = pd.Series(True, index=df.index)
    
    # At least one text field (abstract or keywords)
    if "abstract" in df.columns and "keywords" in df.columns:
        has_text = (
            (df["abstract"].notna() & (df["abstract"].str.strip() != "")) |
            (df["keywords"].notna() & (df["keywords"].str.strip() != ""))
        )
        valid_mask &= has_text
    
    # Positive award amounts
    if "award_amount" in df.columns:
        valid_mask &= pd.to_numeric(df["award_amount"], errors="coerce").gt(0)
    
    # Valid dates (not null)
    if "award_date" in df.columns:
        valid_mask &= df["award_date"].notna()
    
    # Required fields present
    for field in ["award_id", "agency"]:
        if field in df.columns:
            valid_mask &= df[field].notna() & (df[field].str.strip() != "")
    
    return df[valid_mask].copy(), df[~valid_mask].copy()


def normalize_agencies_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize agency names in batch using vectorized operations.
    
    Args:
        df: DataFrame with 'agency' column
        
    Returns:
        DataFrame with normalized agency codes
    """
    if "agency" not in df.columns:
        return df
    
    # Vectorized agency normalization
    df["agency"] = df["agency"].apply(normalize_agency_name)
    
    return df


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Optimize DataFrame dtypes for memory efficiency.
    
    Args:
        df: DataFrame to optimize
        
    Returns:
        DataFrame with optimized dtypes
    """
    # Categorical columns (limited unique values)
    categorical_cols = ["agency", "sub_agency", "phase", "firm_state"]
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype("category")
    
    # String columns
    string_cols = ["award_id", "topic_code", "abstract", "firm_name", "firm_city"]
    for col in string_cols:
        if col in df.columns and df[col].dtype == "object":
            df[col] = df[col].astype("string")
    
    # Numeric optimizations
    if "award_amount" in df.columns:
        df["award_amount"] = pd.to_numeric(df["award_amount"], errors="coerce")
    
    if "solicitation_year" in df.columns:
        df["solicitation_year"] = pd.to_numeric(df["solicitation_year"], errors="coerce").astype("Int16")
    
    return df
