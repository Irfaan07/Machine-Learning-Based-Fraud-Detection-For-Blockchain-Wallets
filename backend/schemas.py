from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ScanWalletRequest(BaseModel):
    wallet_address: str = Field(..., min_length=4, max_length=128)
    blockchain: Literal["ethereum", "bitcoin"]


class FlagScanRequest(BaseModel):
    feedback: int = Field(..., description="1 for Confirmed Fraud, 0 for False Positive")


class WalletScanBase(BaseModel):
    scan_id: int
    wallet_address: str
    blockchain: str
    transaction_count: int
    avg_value: float
    max_value: float
    std_value: float
    transaction_frequency: float
    burst_activity: float
    xgboost_score: float
    lightgbm_score: float
    fraud_probability: float
    risk_level: str
    shap_data: str | None = None
    user_feedback: int | None = None
    timestamp: datetime

    class Config:
        from_attributes = True


class BatchScanResponse(BaseModel):
    successful: list[ScanWalletResponse]
    failed: list[dict]


class ScanWalletResponse(WalletScanBase):
    pass


class ScanHistoryResponse(BaseModel):
    scans: list[WalletScanBase]

