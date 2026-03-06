# Kernel: sales-kpi-aggregator

__pattern__ = "TemplateMethod"
__domain__ = "sales"
__uses__ = 1
__source_problem__ = "9fc5c831-035a-4dfd-b252-9a4ccfd5cd9a"
__verdict__ = "pass"
__created__ = "2026-03-06"

## Purpose

Generate synthetic multi-dimensional sales data and compute standard KPIs:
revenue by region, by sales rep, monthly trends, and a linear regression
performance baseline. Produces cleaned CSV + markdown report.

## Key Decisions

- `np.random.seed(42)` — reproducible synthetic data generation
- 5% missing values injected (discount + units_sold) to test cleaning
- Missing numeric imputed with mean/median (not drop) to preserve sample size
- Revenue = `units_sold × unit_price × (1 − discount)` — standard retail formula
- LinearRegression on `[month, units_sold, unit_price, discount]` → revenue
- R² is intentionally low for random data; MSE is the primary diagnostic

## Template Steps

1. `generate_sample_data()` — synthetic DataFrame with date, product, rep, region, price
2. `clean_data(df)` — dropna(all), fillna(mean/median), drop_duplicates
3. `perform_analysis(df)` — groupby aggregations: region, rep, month
4. `build_model(df)` — train/test split 80/20, LinearRegression, MSE + R²
5. Write `sales_analysis_report.md` + `model_metrics.json`

## Reuse Pattern

```python
# Adapt column names; keep the 5-step template order
from sklearn.linear_model import LinearRegression
df = generate_sample_data()
df = clean_data(df)
kpis = perform_analysis(df)
model, metrics = build_model(df)
```

## Artefacts Produced

- `cleaned_data.csv` — clean sales DataFrame
- `sales_analysis_plot.png` — matplotlib revenue trend chart
- `data-scientist_output.md` — KPI summary report with model metrics

## Known Limitations

- R² ≈ −0.02 on purely random data; add seasonality signal for better fit
- Single-year data; add year feature for multi-year trends
