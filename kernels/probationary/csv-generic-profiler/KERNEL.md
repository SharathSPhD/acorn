# Kernel: csv-generic-profiler

__pattern__ = "Strategy"
__domain__ = "analysis"
__version__ = "0.1.0-probationary"
__uses__ = 1
__source_problem__ = "b8edf36c-a8dd-4b2f-b51a-22c665526a11"
__verdict__ = "pass"
__created__ = "2026-03-06"

## Purpose

This kernel provides a generic CSV profiler that reads one or more CSV files from a workspace, combines them, and computes statistics using different strategies for numeric vs categorical columns. It cleans data by dropping NA rows and generates a markdown report.

## Pattern Description

The Strategy pattern applies different analysis strategies for numeric columns (e.g., describe-based statistics) and categorical columns (e.g., mode). The profiler selects the appropriate strategy per column type and aggregates results into a unified report.

## Template Steps

1. Discover and load CSV files from workspace
2. Combine dataframes (concat)
3. Apply numeric strategy: describe() for numeric columns
4. Apply categorical strategy: mode() for object columns
5. Clean (dropna) and write report

## Example Usage

```python
import os
import pandas as pd
import numpy as np


def _numeric_strategy(df: pd.DataFrame) -> dict:
    """Strategy for numeric columns: describe()."""
    num_df = df.select_dtypes(include=[np.number])
    if num_df.empty:
        return {}
    return num_df.describe().to_dict()


def _categorical_strategy(df: pd.DataFrame) -> dict:
    """Strategy for categorical columns: mode()."""
    cat_df = df.select_dtypes(include=["object"])
    if cat_df.empty:
        return {}
    return cat_df.mode().iloc[0].to_dict()


def profile_csv(
    workspace_dir: str | None = None,
    output_path: str | None = None,
) -> dict:
    """Profile all CSVs in workspace_dir.

    Returns dict with keys: total_files, total_records, stats_computed, cleaned_path.
    """
    base = workspace_dir or os.getcwd()
    csv_files = [f for f in os.listdir(base) if f.endswith(".csv")]
    if not csv_files:
        return {"total_files": 0, "total_records": 0, "stats_computed": False, "cleaned_path": None}

    dfs = []
    for fname in csv_files:
        df = pd.read_csv(os.path.join(base, fname))
        if len(df) > 0:
            dfs.append(df)

    if not dfs:
        return {"total_files": len(csv_files), "total_records": 0, "stats_computed": False, "cleaned_path": None}

    combined = pd.concat(dfs, ignore_index=True)

    # Apply strategies by column type
    numeric_stats = _numeric_strategy(combined)
    categorical_stats = _categorical_strategy(combined)
    stats = {"numerical_description": numeric_stats}
    if categorical_stats:
        stats["categorical_mode"] = categorical_stats

    # Clean and save
    cleaned = combined.dropna()
    cleaned_path = os.path.join(base, "cleaned_data.csv")
    cleaned.to_csv(cleaned_path, index=False)

    # Write markdown report
    out_path = output_path or os.path.join(base, "csv_profile_report.md")
    lines = [
        "# CSV Statistics Report",
        f"Files processed: {len(csv_files)}",
        f"Total records: {len(combined)}",
        f"Records after cleaning: {len(cleaned)}",
    ]
    if "numerical_description" in stats:
        lines.append("\n## Numerical Statistics")
        for col, col_stats in stats["numerical_description"].items():
            lines.append(f"\n### {col}")
            for stat_name, val in col_stats.items():
                lines.append(f"- {stat_name}: {val:.4f}")

    if "categorical_mode" in stats:
        lines.append("\n## Categorical Modes")
        for col, mode_val in stats["categorical_mode"].items():
            lines.append(f"- {col}: {mode_val}")

    with open(out_path, "w") as f:
        f.write("\n".join(lines))

    return {
        "total_files": len(csv_files),
        "total_records": len(combined),
        "stats_computed": bool(stats),
        "cleaned_path": cleaned_path,
    }
```

## Dependencies

pandas, numpy

## Promotion Criteria

Must be used in ≥2 independent problems to promote from probationary to permanent.
