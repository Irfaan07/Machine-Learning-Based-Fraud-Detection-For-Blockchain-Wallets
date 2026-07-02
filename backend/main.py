from __future__ import annotations

from datetime import datetime
import csv
import io
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from data_collection import (
    get_eth_transactions,
    get_btc_transactions,
    BlockchainAPIError,
)
import auth
from auth import get_current_user
from config import settings
from database import WalletScan, get_db, init_db
from feature_engineering import compute_features
from model_loader import load_model, reload_model
from models_user import User
from schemas import ScanWalletRequest, ScanWalletResponse, ScanHistoryResponse, FlagScanRequest, BatchScanResponse


app = FastAPI(title="AI-Powered Blockchain Wallet Fraud Detection API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    # warm up model
    load_model()


app.include_router(auth.router)


async def _fetch_and_engineer_features(wallet_address: str, blockchain: str):
    if blockchain == "ethereum":
        parsed = await get_eth_transactions(wallet_address)
    else:
        parsed = await get_btc_transactions(wallet_address)

    features = compute_features(wallet_address, parsed)
    return features


DBSessionDep = Annotated[Session, Depends(get_db)]


CurrentUserDep = Annotated[User, Depends(get_current_user)]


@app.post("/scan-wallet", response_model=ScanWalletResponse)
async def scan_wallet(payload: ScanWalletRequest, db: DBSessionDep, current_user: CurrentUserDep):
    try:
        features = await _fetch_and_engineer_features(payload.wallet_address, payload.blockchain)
    except BlockchainAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error fetching blockchain data: {e}")

    model = load_model()
    result = model.predict([
        float(features.transaction_count),
        float(features.avg_transaction_value),
        float(features.max_transaction_value),
        float(features.std_transaction_value),
        float(features.transaction_frequency),
        float(features.active_time_span),
        float(features.large_transaction_ratio),
        float(features.burst_transaction_activity),
        float(features.incoming_outgoing_ratio),
    ])

    scan = WalletScan(
        user_id=current_user.id,
        wallet_address=payload.wallet_address,
        blockchain=payload.blockchain,
        transaction_count=features.transaction_count,
        avg_value=features.avg_transaction_value,
        max_value=features.max_transaction_value,
        std_value=features.std_transaction_value,
        transaction_frequency=features.transaction_frequency,
        burst_activity=features.burst_transaction_activity,
        xgboost_score=result["xgboost_score"],
        lightgbm_score=result["lightgbm_score"],
        fraud_probability=result["final_score"],
        risk_level=result["risk_level"],
        shap_data=result.get("shap_data"),
        timestamp=datetime.utcnow(),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    return ScanWalletResponse.model_validate(scan, from_attributes=True)


@app.post("/scan-batch", response_model=BatchScanResponse)
async def scan_batch(
    file: UploadFile = File(...),
    db: DBSessionDep = None,
    current_user: CurrentUserDep = None,
):
    contents = await file.read()
    decoded = contents.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    
    results = []
    failed = []
    model = load_model()
    
    for row in reader:
        wallet = row.get("wallet_address")
        if not wallet:
            continue
        wallet = wallet.strip()
            
        blockchain = row.get("blockchain", "").strip().lower()
        if not blockchain:
            blockchain = "ethereum" if wallet.startswith("0x") else "bitcoin"
            
        try:
            features = await _fetch_and_engineer_features(wallet, blockchain)
            X = [
                float(features.transaction_count),
                float(features.avg_transaction_value),
                float(features.max_transaction_value),
                float(features.std_transaction_value),
                float(features.transaction_frequency),
                float(features.active_time_span),
                float(features.large_transaction_ratio),
                float(features.burst_transaction_activity),
                float(features.incoming_outgoing_ratio),
            ]
            result = model.predict(X)
            
            scan = WalletScan(
                user_id=current_user.id,
                wallet_address=wallet,
                blockchain=blockchain,
                xgboost_score=result["xgboost_score"],
                lightgbm_score=result["lightgbm_score"],
                fraud_probability=result["final_score"],
                risk_level=result["risk_level"],
                shap_data=result.get("shap_data"),
                timestamp=datetime.utcnow(),
            )
            db.add(scan)
            db.commit()
            db.refresh(scan)
            
            res = ScanWalletResponse.model_validate(scan, from_attributes=True)
            results.append(res)
        except Exception as e:
            print(f"Failed batch scan for {wallet}: {e}")
            failed.append({"wallet": wallet, "error": str(e)})
            continue
            
    return BatchScanResponse(successful=results, failed=failed)


@app.get("/scan-history", response_model=ScanHistoryResponse)
def scan_history(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    limit: int = Query(50, ge=1, le=500),
):
    scans = (
        db.query(WalletScan)
        .filter(WalletScan.user_id == current_user.id)
        .order_by(WalletScan.timestamp.desc())
        .limit(limit)
        .all()
    )
    return ScanHistoryResponse(scans=scans)


@app.post("/flag-scan/{scan_id}")
def flag_scan(
    scan_id: int,
    payload: FlagScanRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    scan = db.query(WalletScan).filter(WalletScan.scan_id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to flag this scan")
        
    scan.user_feedback = payload.feedback
    db.commit()
    return {"message": "Feedback recorded successfully"}


@app.post("/retrain")
def retrain_model(current_user: CurrentUserDep):
    # In production, require admin role here. 
    import train_model
    try:
        train_model.train_models()
        reload_model()
        return {"message": "Model retrained and reloaded successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {e}")

app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")



