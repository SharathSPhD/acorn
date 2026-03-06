# Kernel: telemetry-analysis

__pattern__ = "TemplateMethod"

## Purpose

Analyze agent telemetry CSV data: validate schema, compute event-type distributions,
identify per-agent activity patterns, assess data quality, and produce a markdown
recommendations report with summary metrics JSON.

## Source Problem

`2fded6f1-3d18-4e12-a1fc-de2f52464081` — Analyze ACORN system telemetry

## When to Reuse

- Any problem requiring event-type frequency analysis from a timestamped telemetry CSV
- Agent activity pattern detection (group-by agent + event type)
- Data quality assessment with missing-value reporting
- Automated markdown report generation from tabular data

## Template Method Steps

1. **load_data()** — Read CSV, report shape
2. **validate_schema()** — Assert required columns (`event_type`, `timestamp`, `agent_id`)
3. **clean_data()** — Drop nulls, parse timestamps
4. **compute_event_counts()** — `value_counts()` on event_type
5. **detect_agent_patterns()** — Group by (agent_id, event_type), rank most active
6. **assess_data_quality()** — Null audit per column
7. **generate_recommendations()** — Threshold-based heuristics (event diversity, agent count, rare events)
8. **write_artifacts()** — Save cleaned CSV, metrics JSON, markdown report

## Example

```python
import pandas as pd
import json

def analyze_telemetry(input_csv: str, output_dir: str) -> dict:
    """Template method: load -> validate -> clean -> analyze -> report."""
    # 1. Load
    df = pd.read_csv(input_csv)

    # 2. Validate
    required = ["event_type", "timestamp", "agent_id"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # 3. Clean
    df = df.dropna()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # 4. Event counts
    event_counts = df["event_type"].value_counts()

    # 5. Agent patterns
    agent_activity = (
        df.groupby(["agent_id", "event_type"])
        .size()
        .reset_index(name="count")
    )
    top_agents = (
        agent_activity.groupby("agent_id")["count"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    # 6. Data quality
    null_audit = df.isnull().sum()

    # 7. Recommendations
    recs = []
    if len(event_counts) > 10:
        recs.append("High event-type diversity — consider consolidating categories.")
    if df["agent_id"].nunique() < 10:
        recs.append("Few agents detected — expand telemetry collection.")
    rare = event_counts[event_counts < 5]
    if len(rare) > 0:
        recs.append(f"{len(rare)} rare event types: {list(rare.index)}")

    # 8. Write artifacts
    metrics = {
        "total_records": len(df),
        "unique_event_types": len(event_counts),
        "unique_agents": int(df["agent_id"].nunique()),
        "event_distribution": event_counts.to_dict(),
        "top_agents": top_agents.to_dict(),
    }

    report_lines = [
        "# Telemetry Analysis Report",
        f"\nTotal records: {len(df)}",
        f"Unique event types: {len(event_counts)}",
        f"Unique agents: {df['agent_id'].nunique()}",
        "\n## Event Distribution",
        "| Event Type | Count | % |",
        "|---|---|---|",
    ]
    for etype, cnt in event_counts.items():
        pct = cnt / len(df) * 100
        report_lines.append(f"| {etype} | {cnt} | {pct:.1f}% |")

    report_lines.append("\n## Recommendations")
    for i, r in enumerate(recs, 1):
        report_lines.append(f"{i}. {r}")

    with open(f"{output_dir}/telemetry_report.md", "w") as f:
        f.write("\n".join(report_lines))
    with open(f"{output_dir}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    df.to_csv(f"{output_dir}/cleaned_data.csv", index=False)

    return metrics
```

## Dependencies

- pandas
- numpy (optional, for advanced stats)

## Limitations

- Assumes flat CSV input (not direct DB query)
- Recommendations are heuristic-based, not ML-driven
- Original problem failed due to missing input data (no CSV in workspace)
