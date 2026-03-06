# Kernel: Customer Churn Classifier

__pattern__ = "Strategy"
__version__ = "0.1.0-probationary"
__source_problem__ = "7a27ccf1"
__uses__ = 1

## Pattern
Trains a RandomForestClassifier on tabular customer data to predict binary churn.
Pipeline: load CSV, engineer temporal and behavioural features, encode categoricals,
train/test split (80/20, stratified), fit RandomForest(n_estimators=100), evaluate
with AUC-ROC and classification report, output feature importances.

## Use Cases
- Customer retention analysis
- Subscription churn prediction
- Any binary classification on tabular customer data with plan/spend/activity features

## Python Example
```python
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score
import json


def clean_and_engineer(df: pd.DataFrame) -> pd.DataFrame:
    """Clean customer data and engineer churn-predictive features."""
    df["signup_date"] = pd.to_datetime(df["signup_date"])
    df["last_active"] = pd.to_datetime(df["last_active"])
    df["days_since_active"] = (datetime.now() - df["last_active"]).dt.days
    df["customer_lifetime_days"] = (df["last_active"] - df["signup_date"]).dt.days
    df["days_active"] = df["customer_lifetime_days"]
    df["engagement_score"] = df["days_active"] * df["monthly_spend"] / 1000
    df["months_since_signup"] = (datetime.now() - df["signup_date"]).dt.days / 30
    df["inactive_months"] = df["days_since_active"] / 30
    le = LabelEncoder()
    df["plan_type_encoded"] = le.fit_transform(df["plan_type"])
    return df


def train_churn_model(
    input_path: str,
    metrics_path: str,
    test_size: float = 0.2,
    n_estimators: int = 100,
    random_state: int = 42,
) -> dict:
    """Train a RandomForest churn classifier and save metrics."""
    df = pd.read_csv(input_path)
    df = clean_and_engineer(df)

    features = [
        "plan_type_encoded",
        "monthly_spend",
        "support_tickets",
        "days_since_active",
        "engagement_score",
        "months_since_signup",
        "inactive_months",
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
    }
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    importance = pd.DataFrame(
        {"feature": features, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)

    return {"model": model, "metrics": metrics, "feature_importance": importance}
```

## Dependencies
pandas, numpy, scikit-learn

## Promotion Criteria
- Used in >= 2 independent problems (ACORN_KERNEL_PROMO_THRESHOLD=2)
- Judge PASS on both uses
- No hardcoded paths
