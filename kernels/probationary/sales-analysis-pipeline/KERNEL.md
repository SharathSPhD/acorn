# Kernel: Sales Analysis Pipeline

__pattern__ = "Strategy"
__version__ = "0.1.0-probationary"
__source_problem__ = "cc9fb02e"
__uses__ = 1

## Pattern
End-to-end sales data analysis: load and clean CSV (median-impute missing values),
compute product-level and region-level KPIs, build a correlation matrix, fit a
LinearRegression model predicting sales volume from price/marketing/rating, and
output metrics (MSE, R2, feature coefficients).

## Use Cases
- Sales performance reporting by product and region
- Marketing spend ROI analysis
- Sales volume forecasting from pricing and marketing features
- Any tabular sales dataset with product/region/spend/rating columns

## Python Example
```python
import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score


def load_and_clean(input_path: str) -> pd.DataFrame:
    """Load sales CSV and median-impute missing numeric values."""
    df = pd.read_csv(input_path)
    for col in ["unit_price", "marketing_spend", "customer_rating"]:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())
    df.dropna(inplace=True)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


def analyze_sales(df: pd.DataFrame) -> dict:
    """Compute product-level, region-level aggregates and correlations."""
    product_kpis = (
        df.groupby("product_id")
        .agg(
            total_volume=("sales_volume", "sum"),
            avg_volume=("sales_volume", "mean"),
            txn_count=("sales_volume", "count"),
            avg_price=("unit_price", "mean"),
            total_marketing=("marketing_spend", "sum"),
        )
        .round(2)
    )

    region_kpis = (
        df.groupby("region")
        .agg(
            total_volume=("sales_volume", "sum"),
            avg_volume=("sales_volume", "mean"),
            avg_price=("unit_price", "mean"),
        )
        .round(2)
    )

    numeric_cols = ["sales_volume", "unit_price", "marketing_spend", "customer_rating"]
    corr = df[[c for c in numeric_cols if c in df.columns]].corr()

    return {
        "product_kpis": product_kpis,
        "region_kpis": region_kpis,
        "correlation_matrix": corr,
    }


def build_sales_model(
    df: pd.DataFrame,
    metrics_path: str,
    feature_cols: list[str] | None = None,
    target_col: str = "sales_volume",
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict:
    """Fit LinearRegression on sales data and save metrics."""
    if feature_cols is None:
        feature_cols = ["unit_price", "marketing_spend", "customer_rating"]

    model_df = df[feature_cols + [target_col]].dropna()
    X = model_df[feature_cols]
    y = model_df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "mse": float(mean_squared_error(y_test, y_pred)),
        "r2_score": float(r2_score(y_test, y_pred)),
        "feature_importance": dict(zip(feature_cols, [float(c) for c in model.coef_])),
    }
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    return {"model": model, "metrics": metrics}
```

## Dependencies
pandas, numpy, scikit-learn

## Promotion Criteria
- Used in >= 2 independent problems (ACORN_KERNEL_PROMO_THRESHOLD=2)
- Judge PASS on both uses
- No hardcoded paths
