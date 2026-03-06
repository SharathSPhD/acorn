# Kernel: churn-prediction-rf

__pattern__ = "TemplateMethod"
__domain__ = "customer"
__version__ = "0.1.0-probationary"
__uses__ = 1
__source_problem__ = "7a27ccf1-b8ad-41b5-a204-930f3c24b6c4"
__verdict__ = "pass"
__created__ = "2026-03-06"

## Purpose

This kernel implements an end-to-end customer churn prediction pipeline using RandomForestClassifier. It orchestrates data generation or loading, cleaning, feature engineering, exploratory analysis, model training, and report generation in a fixed sequence. The pipeline is designed for binary churn classification on tabular customer data with plan, spend, and activity features.

## Pattern Description

The TemplateMethod pattern defines the skeleton of the churn analysis algorithm: generate (or load) → clean → analyze → model → report. Each step is implemented as a method that subclasses or callers can override if needed, but the overall flow remains fixed. The pattern ensures consistent structure across churn analyses while allowing step-specific customization.

## Template Steps

1. Data Generation/Loading
2. Data Cleaning & Feature Engineering
3. Exploratory Data Analysis
4. Model Training (RandomForest)
5. Evaluation & Report Generation

## Example Usage

```python
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score


def load_or_generate_data(data_path: str | None = None) -> pd.DataFrame:
    """Step 1: Load CSV or generate synthetic churn data."""
    if data_path and os.path.exists(data_path):
        return pd.read_csv(data_path)
    # Synthetic fallback for demo
    base = os.getcwd()
    np.random.seed(42)
    n = 500
    return pd.DataFrame({
        "signup_date": pd.date_range("2023-01-01", periods=n, freq="D"),
        "last_active": pd.date_range("2024-01-01", periods=n, freq="D"),
        "plan_type": np.random.choice(["basic", "premium", "enterprise"], n),
        "monthly_spend": np.random.uniform(20, 200, n),
        "support_tickets": np.random.randint(0, 10, n),
        "churned": np.random.binomial(1, 0.3, n),
    })


def clean_and_engineer(df: pd.DataFrame) -> pd.DataFrame:
    """Step 2: Clean and engineer churn-predictive features."""
    df["signup_date"] = pd.to_datetime(df["signup_date"])
    df["last_active"] = pd.to_datetime(df["last_active"])
    df["days_since_active"] = (datetime.now() - df["last_active"]).dt.days
    df["customer_lifetime_days"] = (df["last_active"] - df["signup_date"]).dt.days
    df["days_active"] = df["customer_lifetime_days"]
    df["engagement_score"] = df["days_active"] * df["monthly_spend"] / 1000
    df["months_since_signup"] = (datetime.now() - df["signup_date"]).dt.days / 30
    df["inactive_months"] = df["days_since_active"] / 30
    le = LabelEncoder()
    df["plan_type_encoded"] = le.fit_transform(df["plan_type"].astype(str))
    return df


def run_eda(df: pd.DataFrame) -> dict:
    """Step 3: Exploratory data analysis."""
    return {
        "shape": df.shape,
        "churn_rate": df["churned"].mean(),
        "numeric_summary": df.select_dtypes(include=[np.number]).describe().to_dict(),
    }


def train_and_evaluate(
    df: pd.DataFrame,
    output_dir: str | None = None,
    test_size: float = 0.2,
    n_estimators: int = 100,
    random_state: int = 42,
) -> dict:
    """Steps 4–5: Train RandomForest, evaluate, generate report."""
    features = [
        "plan_type_encoded", "monthly_spend", "support_tickets",
        "days_since_active", "engagement_score", "months_since_signup", "inactive_months",
    ]
    X = df[features].fillna(0)
    y = df["churned"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    model = RandomForestClassifier(n_estimators=n_estimators, random_state=random_state)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)

    metrics = {
        "auc_score": auc,
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
        "feature_importance": dict(zip(features, model.feature_importances_)),
    }

    out_dir = output_dir or os.getcwd()
    metrics_path = os.path.join(out_dir, "churn_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    return {"model": model, "metrics": metrics}


def run_churn_pipeline(data_path: str | None = None, output_dir: str | None = None) -> dict:
    """Execute full TemplateMethod pipeline."""
    df = load_or_generate_data(data_path)
    df = clean_and_engineer(df)
    eda = run_eda(df)
    result = train_and_evaluate(df, output_dir=output_dir)
    return {"eda": eda, **result}
```

## Dependencies

pandas, numpy, scikit-learn, matplotlib, seaborn

## Promotion Criteria

Must be used in ≥2 independent problems to promote from probationary to permanent.
