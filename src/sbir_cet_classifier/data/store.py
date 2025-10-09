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
) -> Path:
    """Write a dataframe to `root/<partition>/<filename>`."""

    target = _partition_dir(root, partition) / filename
    frame.to_parquet(target, index=False)
    return target


def read_partition(
    root: Path,
    partition: str | int,
    *,
    filename: str = DEFAULT_FILENAME,
    columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Read a parquet partition back into a dataframe."""

    path = root / str(partition) / filename
    if not path.exists():
        raise FileNotFoundError(f"Partition not found: {path}")
    return pd.read_parquet(path, columns=list(columns) if columns else None)


def list_partitions(root: Path) -> list[str]:
    """Return available partition labels under `root`."""

    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


__all__ = ["write_partition", "read_partition", "list_partitions", "DEFAULT_FILENAME"]
