# Kernel: Sales Forecasting Regression

__pattern__ = "TemplateMethod"
__version__ = "0.1.0-probationary"
__source_problem__ = "cc9fb02e"
__uses__ = 1

## Pattern
TemplateMethod pipeline for sales forecasting: clean data (drop nulls, remove
outliers via 99th-percentile threshold, parse dates), engineer temporal features
(year, month, day_of_week), one-hot encode categorical columns (region, segment),
fit LinearRegression, evaluate with RMSE and R2, report feature coefficients.

The template steps are: clean -> engineer_features -> encode -> train -> evaluate -> report.
Subclasses or callers can override individual steps (e.g. swap LinearRegression for
GradientBoosting) while preserving the pipeline structure.

## Use Cases
- Sales volume forecasting with temporal seasonality
- Revenue prediction across regions and customer segments
- Any tabular regression with date + categorical + numeric features
- Demand planning pipelines needing temporal feature engineering

## Python Example
```python
import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score


def clean_data(df: pd.DataFrame, target_col: str = "sales_amount") -> pd.DataFrame:
    """Drop nulls, remove outliers, parse dates, sort chronologically."""
    df = df.dropna()
    threshold = df[target_col].quantile(0.99) * 10
    df = df[df[target_col] <= threshold]
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    return df


def engineer_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract year, month, day_of_week from date column."""
    df["year"] = df["date"].dt.year
    df["month_num"] = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.dayofweek
    return df


def encode_categoricals(
    df: pd.DataFrame, columns: list[str], drop_first: bool = True
) -> pd.DataFrame:
    """One-hot encode categorical columns."""
    return pd.get_dummies(df, columns=columns, drop_first=drop_first)


def train_forecast_model(
    df: pd.DataFrame,
    target_col: str = "sales_amount",
    categorical_cols: list[str] | None = None,
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict:
    """Full TemplateMethod pipeline: clean, engineer, encode, train, evaluate."""
    if categorical_cols is None:
        categorical_cols = ["region", "customer_segment"]

    df = clean_data(df, target_col)
    df = engineer_temporal_features(df)
    df = encode_categoricals(df, categorical_cols)

    temporal_features = ["year", "month_num", "day_of_week"]
    encoded_features = [
        c for c in df.columns
        if any(c.startswith(f"{cat}_") for cat in categorical_cols)
    ]
    feature_cols = temporal_features + encoded_features

    X = df[feature_cols]
    y = df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "r2_score": float(r2_score(y_test, y_pred)),
        "feature_importance": dict(
            zip(feature_cols, [float(c) for c in model.coef_])
        ),
    }
    return {"model": model, "metrics": metrics}


def save_metrics(metrics: dict, output_path: str) -> None:
    """Persist model metrics to JSON."""
    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=2)
```

## Dependencies
pandas, numpy, scikit-learn

## Promotion Criteria
- Used in >= 2 independent problems (ACORN_KERNEL_PROMO_THRESHOLD=2)
- Judge PASS on both uses
- No hardcoded paths
