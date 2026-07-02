import csv
import logging
import os
import time

from data_collection import get_btc_transactions
from feature_engineering import compute_features

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dummy representation of labelled subset from Elliptic dataset
# In a real environment, this would read from elliptic_txs.csv mapping to wallets.
DUMMY_LABELED_WALLETS = [
    {"wallet": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "label": 0},  # Satoshi (likely benign)
    {"wallet": "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo", "label": 0},  # Binance cold wallet
    {"wallet": "1Ez69SnzzmePmZX3WpEzMKTrcBF2gpNQ55", "label": 1},  # Known scam/hack example shape
]

DATASET_FILE = "data/wallet_dataset.csv"

async def build_dataset():
    """
    Connects to the Elliptic dataset equivalents, fetches realtime APIs, handles rate limits,
    processes via feature engine, and writes to the ML csv file.
    """
    os.makedirs(os.path.dirname(DATASET_FILE), exist_ok=True)
    
    logger.info("Starting Dataset Builder pipeline...")
    
    headers = [
        "wallet_address",
        "transaction_count",
        "avg_value",
        "max_value",
        "std_value",
        "transaction_frequency",
        "active_time_span",
        "large_transaction_ratio",
        "burst_activity",
        "incoming_outgoing_ratio",
        "label"
    ]
    
    with open(DATASET_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for record in DUMMY_LABELED_WALLETS:
            wallet = record["wallet"]
            label = record["label"]
            
            logger.info(f"Processing wallet: {wallet}")
            try:
                # Assuming Elliptic is strictly Bitcoin
                txs = await get_btc_transactions(wallet)
                features = compute_features(wallet, txs)
                
                row = [
                    wallet,
                    features.transaction_count,
                    features.avg_transaction_value,
                    features.max_transaction_value,
                    features.std_transaction_value,
                    features.transaction_frequency,
                    features.active_time_span,
                    features.large_transaction_ratio,
                    features.burst_transaction_activity,
                    features.incoming_outgoing_ratio,
                    label
                ]
                writer.writerow(row)
                
                # Respect real-world rate limits
                time.sleep(2)
            except Exception as e:
                logger.error(f"Failed to process {wallet}: {e}")

    logger.info(f"Dataset securely built and saved to {DATASET_FILE}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(build_dataset())
