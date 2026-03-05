# Kernel: CSV Statistical Report

__pattern__ = "TemplateMethod"
__version__ = "0.1.0-probationary"
__source_problem__ = "b8edf36c"
__uses__ = 1

## Pattern
Reads one or more CSV files from a workspace directory, computes descriptive statistics
(numerical summary via pandas describe, categorical mode), cleans data by dropping NA rows,
and generates a markdown report.

## Use Cases
- Quick EDA on tabular sales/operational data
- Automated reporting from uploaded CSV files
- First-pass data quality assessment before deeper analysis

## Python Example

```python
import os
import pandas as pd
import numpy as np


def csv_stats_report(workspace_dir: str, output_path: str) -> dict:
    """Generate a statistical report from all CSVs in workspace_dir.

    Returns a dict with keys: total_files, total_records, stats_computed, cleaned_path.
    """
    csv_files = [f for f in os.listdir(workspace_dir) if f.endswith(".csv")]
    if not csv_files:
        return {"total_files": 0, "total_records": 0, "stats_computed": False, "cleaned_path": None}

    dfs = []
    for fname in csv_files:
        df = pd.read_csv(os.path.join(workspace_dir, fname))
        if len(df) > 0:
            dfs.append(df)

    if not dfs:
        return {"total_files": len(csv_files), "total_records": 0, "stats_computed": False, "cleaned_path": None}

    combined = pd.concat(dfs, ignore_index=True)

    # Numerical statistics
    stats = {}
    num_df = combined.select_dtypes(include=[np.number])
    if not num_df.empty:
        stats["numerical_description"] = num_df.describe().to_dict()

    # Categorical mode
    cat_df = combined.select_dtypes(include=["object"])
    if not cat_df.empty:
        stats["categorical_mode"] = cat_df.mode().iloc[0].to_dict()

    # Clean and save
    cleaned = combined.dropna()
    cleaned_path = os.path.join(workspace_dir, "cleaned_data.csv")
    cleaned.to_csv(cleaned_path, index=False)

    # Write markdown report
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

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return {
        "total_files": len(csv_files),
        "total_records": len(combined),
        "stats_computed": bool(stats),
        "cleaned_path": cleaned_path,
    }
```

## Promotion Criteria
- Used in >= 2 independent problems (ACORN_KERNEL_PROMO_THRESHOLD=2)
- Judge PASS on both
- No hardcoded file paths
