"""Ingest downloaded datasets into ACORN's kernel grove and problem pipeline."""
__pattern__ = "Strategy"

import csv
import json
import os
import sys
from pathlib import Path

import httpx

ACORN_API = os.environ.get("ACORN_API_URL", "http://localhost:8000")
DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"

DATASET_REGISTRY = [
    {
        "domain": "sales",
        "name": "uci-online-retail",
        "file": "sales/online_retail.csv",
        "description": "541K transactions from a UK-based online retailer (2010-2011). Invoice numbers, stock codes, descriptions, quantities, prices, customer IDs, countries.",
        "rows": 541910,
        "licence": "CC BY 4.0",
        "source": "UCI ML Repository",
        "keywords": ["retail", "transactions", "sales", "e-commerce", "revenue"],
        "category": "sales",
    },
    {
        "domain": "customer",
        "name": "telco-customer-churn",
        "file": "customer/telco_churn.csv",
        "description": "7K telecom customers with 21 features including tenure, services, contract type, and binary churn label. From IBM.",
        "rows": 7044,
        "licence": "CC0",
        "source": "IBM / Kaggle",
        "keywords": ["churn", "retention", "telecom", "customer", "attrition"],
        "category": "customer",
    },
    {
        "domain": "marketing",
        "name": "bank-marketing-full",
        "file": "marketing/bank_marketing/bank-additional/bank-additional-full.csv",
        "description": "41K bank marketing campaign contacts with 20 features. Phone call outcomes for term deposit subscription. Semicolon-delimited.",
        "rows": 41189,
        "licence": "CC BY 4.0",
        "source": "UCI ML Repository",
        "keywords": ["marketing", "campaign", "conversion", "bank", "call-centre"],
        "category": "marketing",
    },
    {
        "domain": "human_capital",
        "name": "ibm-hr-attrition",
        "file": "human_capital/ibm_hr_attrition.csv",
        "description": "1470 employees with 35 features including satisfaction, salary, overtime, and binary attrition label.",
        "rows": 1471,
        "licence": "CC0",
        "source": "IBM / Kaggle",
        "keywords": ["attrition", "HR", "employee", "turnover", "retention"],
        "category": "human_capital",
    },
    {
        "domain": "finance",
        "name": "stock-prices-5yr",
        "file": "finance/stock_prices.csv",
        "description": "5 years of daily OHLCV data for 15 major US equities (AAPL, MSFT, GOOGL, AMZN, NVDA, etc).",
        "rows": 18825,
        "licence": "Personal/research",
        "source": "Yahoo Finance via yfinance",
        "keywords": ["stocks", "equities", "OHLCV", "finance", "trading"],
        "category": "finance",
    },
    {
        "domain": "finance",
        "name": "world-bank-indicators",
        "file": "finance/world_bank_indicators.csv",
        "description": "GDP data for ~200 countries from World Bank API (2015-2024).",
        "rows": 490,
        "licence": "CC BY 4.0",
        "source": "World Bank",
        "keywords": ["GDP", "macroeconomics", "countries", "development"],
        "category": "finance",
    },
    {
        "domain": "supply_chain",
        "name": "supply-chain-shipments",
        "file": "supply_chain/shipments.csv",
        "description": "10K shipment records with carrier, origin/destination, lead times, delays, costs. Realistic distributions.",
        "rows": 10000,
        "licence": "Generated",
        "source": "ACORN synthetic",
        "keywords": ["logistics", "shipping", "lead-time", "freight", "supply-chain"],
        "category": "supply_chain",
    },
    {
        "domain": "operations",
        "name": "manufacturing-oee",
        "file": "operations/manufacturing_oee.csv",
        "description": "38K manufacturing OEE records: 20 machines x 3 shifts x 2 years. Throughput, defects, downtime, energy.",
        "rows": 38460,
        "licence": "Generated",
        "source": "ACORN synthetic",
        "keywords": ["OEE", "manufacturing", "throughput", "defects", "downtime"],
        "category": "operations",
    },
    {
        "domain": "product",
        "name": "product-reviews",
        "file": "product/product_reviews.csv",
        "description": "50K product reviews with ratings, sentiment, categories, helpful votes, verification status.",
        "rows": 50000,
        "licence": "Generated",
        "source": "ACORN synthetic",
        "keywords": ["reviews", "ratings", "sentiment", "NPS", "product"],
        "category": "product",
    },
]


def register_kernel(ds: dict) -> dict:
    """Register a dataset as a kernel in ACORN's grove."""
    filepath = DATASETS_DIR / ds["file"]
    if not filepath.exists():
        return {"status": "error", "message": f"File not found: {filepath}"}

    payload = {
        "name": f"dataset-{ds['name']}",
        "category": ds["category"],
        "description": f"[DATASET] {ds['description']} Source: {ds['source']}. Licence: {ds['licence']}. Rows: {ds['rows']}.",
        "trigger_keywords": ds["keywords"],
        "status": "permanent",
        "implementation": f"# Dataset: {ds['name']}\n# Path: {filepath}\n# Rows: {ds['rows']}\nimport pandas as pd\ndf = pd.read_csv('{filepath}')\n",
    }

    try:
        resp = httpx.post(f"{ACORN_API}/api/kernels", json=payload, timeout=10)
        if resp.status_code in (200, 201):
            return {"status": "registered", "name": ds["name"]}
        return {"status": "error", "code": resp.status_code, "body": resp.text[:200]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def submit_problem(title: str, description: str, data_file: str) -> dict:
    """Submit a problem to ACORN using a dataset."""
    filepath = DATASETS_DIR / data_file
    payload = {
        "title": title,
        "description": description,
        "source": "dataset-pipeline",
        "data_manifest": {
            "files": [{"path": str(filepath), "type": "csv"}],
        },
    }

    try:
        resp = httpx.post(f"{ACORN_API}/api/problems", json=payload, timeout=10)
        if resp.status_code in (200, 201):
            pid = resp.json().get("id", "?")
            return {"status": "submitted", "problem_id": pid}
        return {"status": "error", "code": resp.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def copy_to_workspace(problem_id: str, data_file: str) -> bool:
    """Copy dataset to the problem's workspace directory."""
    import shutil
    src = DATASETS_DIR / data_file
    workspace = Path(f"/tmp/acorn-workspaces/problem-{problem_id}")
    workspace.mkdir(parents=True, exist_ok=True)
    dst = workspace / Path(data_file).name
    shutil.copy2(src, dst)
    return dst.exists()


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "register"

    if action == "register":
        print("=== Registering datasets as kernels ===")
        for ds in DATASET_REGISTRY:
            result = register_kernel(ds)
            print(f"  [{result['status']}] {ds['name']} ({ds['domain']})")

    elif action == "problems":
        print("=== Submitting dataset problems to ACORN ===")
        problems = [
            ("Online retail customer segmentation",
             "Using the UCI Online Retail dataset (541K transactions), perform customer segmentation using RFM analysis and KMeans clustering. Identify distinct customer segments, compute segment profiles, and recommend targeted marketing strategies.",
             "sales/online_retail.csv"),
            ("Telco churn prediction with feature importance",
             "Build a churn prediction model on the Telco Customer Churn dataset (7K customers, 21 features). Compare Logistic Regression, Random Forest, and Gradient Boosting. Report AUC-ROC, top-10 feature importances, and retention recommendations.",
             "customer/telco_churn.csv"),
            ("Bank marketing campaign effectiveness analysis",
             "Analyze the Bank Marketing dataset (41K contacts). Determine which customer segments respond best to term deposit campaigns. Build a conversion prediction model and calculate campaign ROI under different targeting strategies.",
             "marketing/bank_marketing/bank-additional/bank-additional-full.csv"),
            ("Stock portfolio risk analysis",
             "Using 5-year OHLCV data for 15 US equities, compute: daily returns, Sharpe ratios, VaR (95%), correlation matrix, optimal Markowitz portfolio. Visualise the efficient frontier.",
             "finance/stock_prices.csv"),
            ("Manufacturing OEE bottleneck analysis",
             "Analyze 38K manufacturing OEE records across 20 machines and 3 shifts. Identify bottleneck machines, shift-level patterns, defect rate trends, and energy efficiency correlations. Recommend throughput improvements.",
             "operations/manufacturing_oee.csv"),
        ]
        for title, desc, data in problems:
            result = submit_problem(title, desc, data)
            print(f"  [{result['status']}] {title[:50]}... -> {result.get('problem_id','?')}")

    else:
        print(f"Usage: {sys.argv[0]} [register|problems]")
