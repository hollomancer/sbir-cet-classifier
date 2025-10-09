from __future__ import annotations

import pandas as pd

from sbir_cet_classifier.data.store import list_partitions, read_partition, write_partition


def test_write_and_read_partition(tmp_path):
    df = pd.DataFrame({"award_id": ["AF123", "NAV456"], "value": [1, 2]})
    output = write_partition(df, tmp_path, partition=2023, filename="awards.parquet")

    assert output.exists()

    loaded = read_partition(tmp_path, 2023, filename="awards.parquet")
    assert loaded.equals(df)
    assert list_partitions(tmp_path) == ["2023"]
