from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

from config import settings


connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


class WalletScan(Base):
    __tablename__ = "wallet_scans"

    scan_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    wallet_address = Column(String(128), index=True, nullable=False)
    blockchain = Column(String(32), index=True, nullable=False)
    transaction_count = Column(Integer, nullable=False)
    avg_value = Column(Float, nullable=False)
    max_value = Column(Float, nullable=False)
    std_value = Column(Float, nullable=False)
    transaction_frequency = Column(Float, nullable=False)
    burst_activity = Column(Float, nullable=False, default=0.0)
    xgboost_score = Column(Float, nullable=False, default=0.0)
    lightgbm_score = Column(Float, nullable=False, default=0.0)
    fraud_probability = Column(Float, nullable=False)
    risk_level = Column(String(16), nullable=False)
    shap_data = Column(String, nullable=True)
    user_feedback = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    
def init_db() -> None:
    import models_user  # noqa: F401 — registers User model with Base metadata
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

