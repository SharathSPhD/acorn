# csv-healing-repair Kernel

**Problem UUID**: b8edf36c-a8dd-4b2f-b51a-22c665526a11

**Pattern**: Repository + Strategy

**Version**: __version__="0.1.0-probationary"

## Problem Statement

When a data analysis pipeline fails, identify the root cause (missing data file, schema error, agent crash, etc.) through telemetry inspection and implement self-healing repair. This kernel provides a reusable framework for diagnosing and fixing CSV-based analysis failures.

## Key Components

### Data Engineer Role
- **File Detection**: Check if expected data files exist at known workspace paths
- **Schema Validation**: Verify CSV structure matches required columns
- **Diagnostics**: Generate detailed failure reports (missing files, schema mismatches, data quality issues)
- **Repair Path**: Suggest corrective actions based on root cause analysis

### Data Scientist Role
- **Fallback Analysis**: Aggregate available CSV files when primary data is missing
- **Robust Statistics**: Calculate statistics on whatever data exists (numerical + categorical)
- **Graceful Degradation**: Handle missing or incomplete data files
- **Report Generation**: Document analysis limitations and successes

## Example Code

```python
# data-engineer_script.py: Diagnostic phase
import pandas as pd
import os
from pathlib import Path

def diagnose_csv_failure():
    """Root cause analysis for CSV processing failures"""
    data_file = "/workspace/agent_telemetry.csv"

    report = []
    report.append("# CSV Analysis Report\n")

    # Check 1: File existence
    if not os.path.exists(data_file):
        report.append("❌ **FAILED**: Data file not found")
        return "\n".join(report)

    # Check 2: Schema validation
    try:
        df = pd.read_csv(data_file)
        required_cols = ['problem_uuid', 'status', 'timestamp', 'message']
        missing = [c for c in required_cols if c not in df.columns]

        if missing:
            report.append(f"❌ Missing required columns: {missing}")
            return "\n".join(report)

        report.append("✅ Schema validated successfully")
        report.append(f"- Rows: {len(df)}")
        report.append(f"- Columns: {list(df.columns)}")

        # Check 3: Data quality
        nulls = df.isnull().sum()
        if nulls.any():
            report.append("\n### Data Quality Issues")
            for col, count in nulls[nulls > 0].items():
                report.append(f"- {col}: {count} missing ({count/len(df)*100:.1f}%)")

        return "\n".join(report)

    except pd.errors.ParserError as e:
        report.append(f"❌ CSV parsing error: {e}")
        return "\n".join(report)

# data-scientist_script.py: Fallback analysis
def fallback_analysis():
    """Graceful degradation when primary data missing"""
    dfs = []

    # Collect all available CSV files
    for file in os.listdir("/workspace"):
        if file.endswith('.csv'):
            try:
                df = pd.read_csv(f"/workspace/{file}")
                if len(df) > 0:
                    dfs.append(df)
            except:
                continue

    if not dfs:
        print("No valid CSV files found")
        return

    # Aggregate and analyze
    combined_df = pd.concat(dfs, ignore_index=True)

    # Calculate robust statistics
    num_cols = combined_df.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        print(f"{col}: mean={combined_df[col].mean():.2f}, std={combined_df[col].std():.2f}")

    # Save cleaned version
    cleaned_df = combined_df.dropna()
    cleaned_df.to_csv("/workspace/cleaned_data.csv", index=False)
```

## Dependencies

- `pandas>=1.0.0` — CSV reading, schema validation, data aggregation
- `numpy>=1.18.0` — Numerical statistics
- `python>=3.8` — Core language

## Judging Criteria

A CSV healing repair solution passes when:

1. **Diagnostics**: Correctly identifies root cause (file missing, schema error, data quality issue)
2. **Repair**: Implements fallback analysis that produces valid output even when primary data unavailable
3. **Reports**: Generates diagnostic markdown report documenting what failed and how it was fixed
4. **Quality**: Cleaned/aggregated data is valid and ready for downstream consumption

## Use Cases

- **Self-healing pipelines**: Detect and repair CSV schema mismatches automatically
- **Data recovery**: Aggregate data from partial sources when primary data lost
- **Diagnostics**: Generate detailed root-cause analysis for failed data jobs
- **Fallback workflows**: Continue analysis gracefully when expected data unavailable

## Probationary Status

This kernel is probationary (v0.1.0) and ready for promotion once it solves 2 independent problems with CSV-based analysis failures. Current coverage: 1 problem (b8edf36c).

---

**Kernel Repository**: `probationary/csv-healing-repair/`
**Authored**: Claude Code v4.5
**Commit**: See `acorn/kernels` branch
