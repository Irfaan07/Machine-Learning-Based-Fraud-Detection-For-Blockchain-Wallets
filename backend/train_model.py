import logging
import os
import pickle

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    accuracy_score,
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATASET_FILE = "data/wallet_dataset.csv"
MODEL_DIR = "models"
XGB_PATH = os.path.join(MODEL_DIR, "xgboost_model.pkl")
LGB_PATH = os.path.join(MODEL_DIR, "lightgbm_model.pkl")

FEATURE_COLS = [
    "transaction_count",
    "avg_value",
    "max_value",
    "std_value",
    "transaction_frequency",
    "active_time_span",
    "large_transaction_ratio",
    "burst_activity",
    "incoming_outgoing_ratio",
]


def evaluate(name: str, clf, X_test, y_test):
    preds = clf.predict(X_test)
    probs = clf.predict_proba(X_test)[:, 1]
    logger.info(f"=== {name} Evaluation ===")
    logger.info(f"Accuracy:  {accuracy_score(y_test, preds):.4f}")
    logger.info(f"Precision: {precision_score(y_test, preds, zero_division=0):.4f}")
    logger.info(f"Recall:    {recall_score(y_test, preds, zero_division=0):.4f}")
    logger.info(f"F1-Score:  {f1_score(y_test, preds, zero_division=0):.4f}")
    if len(y_test.unique()) > 1:
        logger.info(f"ROC-AUC:   {roc_auc_score(y_test, probs):.4f}")
    logger.info(f"Confusion Matrix:\n{confusion_matrix(y_test, preds)}")


def train_models():
    if not os.path.exists(DATASET_FILE):
        logger.error(f"Dataset file {DATASET_FILE} not found. Run dataset_builder.py first.")
        return

    logger.info("Loading base dataset...")
    df = pd.read_csv(DATASET_FILE)
    
    # Active Learning Integration
    try:
        from sqlalchemy import create_engine
        from config import settings
        engine = create_engine(settings.DATABASE_URL)
        query = "SELECT transaction_count, avg_value, max_value, std_value, transaction_frequency, active_time_span, large_transaction_ratio, burst_activity, incoming_outgoing_ratio, user_feedback as label FROM wallet_scans WHERE user_feedback IS NOT NULL"
        df_db = pd.read_sql(query, engine)
        if not df_db.empty:
            logger.info(f"Loaded {len(df_db)} active-learning feedback records from database!")
            df = pd.concat([df, df_db], ignore_index=True)
    except Exception as e:
        logger.warning(f"Could not load active learning data from DB: {e}")

    logger.info(f"Loaded {len(df)} total records. Label distribution: {df['label'].value_counts().to_dict()}")

    if len(df) < 10:
        logger.warning("Dataset is too small. Applying controlled synthetic expansion.")
        rng = np.random.default_rng(42)
        rows = []

        # 60 benign-like wallets (low burst, low value, recurring activity)
        for _ in range(60):
            rows.append({
                "transaction_count": rng.integers(1, 100),
                "avg_value": rng.uniform(0.001, 0.5),
                "max_value": rng.uniform(0.01, 1.0),
                "std_value": rng.uniform(0, 0.2),
                "transaction_frequency": rng.uniform(0.1, 2.0),
                "active_time_span": rng.uniform(30, 365),
                "large_transaction_ratio": rng.uniform(0, 0.2),
                "burst_activity": rng.uniform(0, 0.2),
                "incoming_outgoing_ratio": rng.uniform(0.5, 3.0),
                "label": 0,
            })

        # 40 fraud-like wallets (high burst, large tx, short active span)
        for _ in range(40):
            rows.append({
                "transaction_count": rng.integers(50, 300),
                "avg_value": rng.uniform(1.0, 10.0),
                "max_value": rng.uniform(5.0, 50.0),
                "std_value": rng.uniform(1.0, 5.0),
                "transaction_frequency": rng.uniform(5.0, 30.0),
                "active_time_span": rng.uniform(0.1, 5.0),
                "large_transaction_ratio": rng.uniform(0.5, 1.0),
                "burst_activity": rng.uniform(0.5, 1.0),
                "incoming_outgoing_ratio": rng.uniform(0, 0.3),
                "label": 1,
            })

        synth_df = pd.DataFrame(rows)
        df = pd.concat([df, synth_df], ignore_index=True).sample(frac=1, random_state=42)

    X = df[FEATURE_COLS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    logger.info("Training XGBoost + isotonic calibration...")
    xgb_base = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        scale_pos_weight=len(y_train[y_train == 0]) / max(len(y_train[y_train == 1]), 1),
    )
    from sklearn.calibration import CalibratedClassifierCV
    xgb_clf = CalibratedClassifierCV(xgb_base, cv=3, method="isotonic")
    xgb_clf.fit(X_train, y_train)
    evaluate("XGBoost (calibrated)", xgb_clf, X_test, y_test)

    logger.info("Training LightGBM + isotonic calibration...")
    lgb_base = LGBMClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        random_state=42,
        is_unbalance=True,
    )
    lgb_clf = CalibratedClassifierCV(lgb_base, cv=3, method="isotonic")
    lgb_clf.fit(X_train, y_train)
    evaluate("LightGBM (calibrated)", lgb_clf, X_test, y_test)

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(XGB_PATH, "wb") as f:
        pickle.dump(xgb_clf, f)
    with open(LGB_PATH, "wb") as f:
        pickle.dump(lgb_clf, f)

    logger.info(f"Calibrated models saved to {MODEL_DIR}/")


if __name__ == "__main__":
    train_models()
