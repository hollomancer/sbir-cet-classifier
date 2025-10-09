"""Utilities for reading and writing partitioned Parquet datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

DEFAULT_FILENAME = "data.parquet"


def _partition_dir(root: Path, partition: str | int) -> Path:
    directory = root / str(partition)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_partition(
    frame: pd.DataFrame,
    root: Path,
    partition: str | int,
    *,
    filename: str = DEFAULT_FILENAME,
    compression: str = "snappy",
) -> Path:
    """Write a dataframe to `root/<partition>/<filename>` with optimized settings."""
    target = _partition_dir(root, partition) / filename
    
    # Use optimized parquet settings for better performance
    frame.to_parquet(
        target, 
        index=False,
        compression=compression,
        engine="pyarrow",
        row_group_size=50000,  # Optimize for read performance
    )
    return target


def read_partition(
    root: Path,
    partition: str | int,
    *,
    filename: str = DEFAULT_FILENAME,
    columns: Iterable[str] | None = None,
    use_threads: bool = True,
) -> pd.DataFrame:
    """Read a parquet partition back into a dataframe with optimized settings."""
    path = root / str(partition) / filename
    if not path.exists():
        raise FileNotFoundError(f"Partition not found: {path}")
    
    return pd.read_parquet(
        path, 
        columns=list(columns) if columns else None,
        engine="pyarrow",
        use_threads=use_threads,
    )


def list_partitions(root: Path) -> list[str]:
    """Return available partition labels under `root`."""
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


__all__ = ["write_partition", "read_partition", "list_partitions", "DEFAULT_FILENAME"]
