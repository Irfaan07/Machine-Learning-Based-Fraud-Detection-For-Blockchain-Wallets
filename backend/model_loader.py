from pathlib import Path
from typing import Any

import joblib
import numpy as np
import shap
import json

FEATURE_NAMES = [
    "Transaction Count", "Avg Value", "Max Value", "Std Value", 
    "Tx Frequency", "Active Time Span", "Large Tx Ratio", 
    "Burst Activity", "In/Out Ratio"
]


BASE_PATH = Path(__file__).parent / "models"

XGB_MODEL_PATH = BASE_PATH / "xgboost_model.pkl"
LGB_MODEL_PATH = BASE_PATH / "lightgbm_model.pkl"


class FraudModel:
    def __init__(self, xgb_model: Any, lgb_model: Any):
        self.xgb_model = xgb_model
        self.lgb_model = lgb_model
        
        # Models are CalibratedClassifierCV(cv=3), so we must extract the base estimators for SHAP
        xgb_base = self.xgb_model.calibrated_classifiers_[0].estimator
        lgb_base = self.lgb_model.calibrated_classifiers_[0].estimator
        
        self.xgb_explainer = shap.TreeExplainer(xgb_base)
        self.lgb_explainer = shap.TreeExplainer(lgb_base)

    def predict(self, features: list[float]) -> dict:
        """
        Expects exactly 9 numeric features.
        Returns ensemble risk analysis matching requirement #5.
        """
        X = np.array([features])

        # XGBoost prediction
        xgb_prob = float(self.xgb_model.predict_proba(X)[0][1])

        # LightGBM prediction
        lgb_prob = float(self.lgb_model.predict_proba(X)[0][1])

        # Ensemble average score
        final_prob = float(np.mean([xgb_prob, lgb_prob]))

        if final_prob < 0.3:
            risk = "Low Risk"
        elif final_prob <= 0.7:
            risk = "Medium Risk"
        else:
            risk = "High Risk"

        # Explainability (SHAP)
        xgb_shap = self.xgb_explainer.shap_values(X)
        lgb_shap = self.lgb_explainer.shap_values(X)
        
        if isinstance(xgb_shap, list): xgb_shap = xgb_shap[1]
        if isinstance(lgb_shap, list): lgb_shap = lgb_shap[1]
            
        if len(xgb_shap.shape) > 1: xgb_shap = xgb_shap[0]
        if len(lgb_shap.shape) > 1: lgb_shap = lgb_shap[0]

        mean_shap = np.mean([xgb_shap, lgb_shap], axis=0)
        shap_dict = {FEATURE_NAMES[i]: float(mean_shap[i]) for i in range(len(FEATURE_NAMES))}

        return {
            "xgboost_score": xgb_prob,
            "lightgbm_score": lgb_prob,
            "final_score": final_prob,
            "risk_level": risk,
            "shap_data": json.dumps(shap_dict)
        }


_fraud_model_instance: FraudModel | None = None


def load_model() -> FraudModel:
    global _fraud_model_instance

    if _fraud_model_instance is None:
        if not XGB_MODEL_PATH.exists():
            raise FileNotFoundError(f"XGBoost model not found at {XGB_MODEL_PATH}")

        if not LGB_MODEL_PATH.exists():
            raise FileNotFoundError(f"LightGBM model not found at {LGB_MODEL_PATH}")

        xgb_model = joblib.load(XGB_MODEL_PATH)
        lgb_model = joblib.load(LGB_MODEL_PATH)

        _fraud_model_instance = FraudModel(xgb_model, lgb_model)

    return _fraud_model_instance

def reload_model() -> FraudModel:
    global _fraud_model_instance
    _fraud_model_instance = None
    return load_model()