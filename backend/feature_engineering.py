from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class TransactionFeatures:
    transaction_count: int
    avg_transaction_value: float
    max_transaction_value: float
    std_transaction_value: float
    transaction_frequency: float
    active_time_span: float
    large_transaction_ratio: float
    burst_transaction_activity: float
    incoming_outgoing_ratio: float


def compute_features(wallet_address: str, transactions: list[dict[str, Any]]) -> TransactionFeatures:
    """
    Compute 9 advanced normalized features based on structured transaction data.
    Expected dict format:
    {'value': float, 'timestamp': datetime, 'sender': str, 'receiver': str, ...}
    """
    if not transactions:
        return TransactionFeatures(
            transaction_count=0,
            avg_transaction_value=0.0,
            max_transaction_value=0.0,
            std_transaction_value=0.0,
            transaction_frequency=0.0,
            active_time_span=0.0,
            large_transaction_ratio=0.0,
            burst_transaction_activity=0.0,
            incoming_outgoing_ratio=0.0,
        )

    values = [tx["value"] for tx in transactions if tx.get("value", 0) > 0]
    times = [tx["timestamp"] for tx in transactions if tx.get("timestamp")]
    
    if not values or not times:
        return TransactionFeatures(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    transaction_count = len(values)
    total_value = sum(values)
    avg_transaction_value = total_value / transaction_count
    max_transaction_value = max(values)
    
    # Standard deviation
    variance = sum((v - avg_transaction_value) ** 2 for v in values) / transaction_count if transaction_count > 1 else 0.0
    std_transaction_value = math.sqrt(variance)

    # Active time span (in days)
    min_time = min(times)
    max_time = max(times)
    active_time_span_days = (max_time - min_time).total_seconds() / 86400.0
    active_time_span = max(active_time_span_days, 1.0) # avoid division by zero
    
    # Transaction frequency (tx per day)
    transaction_frequency = transaction_count / active_time_span

    # Large transaction ratio (e.g. greater than 2x average)
    large_threshold = avg_transaction_value * 2 if avg_transaction_value > 0 else 0
    large_txs = sum(1 for v in values if v > large_threshold)
    large_transaction_ratio = large_txs / transaction_count

    # Burst activity: maximum number of transactions within any 1-hour sliding window, normalized
    sorted_times = sorted(times)
    max_in_window = 1
    left = 0
    one_hour = timedelta(hours=1)
    for right in range(len(sorted_times)):
        while sorted_times[right] - sorted_times[left] > one_hour:
            left += 1
        window_size = right - left + 1
        if window_size > max_in_window:
            max_in_window = window_size
            
    burst_transaction_activity = max_in_window / transaction_count

    # Incoming / Outgoing ratio
    incoming_count = 0
    outgoing_count = 0
    for tx in transactions:
        sender = str(tx.get("sender", "")).lower()
        if wallet_address.lower() == sender:
            outgoing_count += 1
        else:
            incoming_count += 1
            
    if incoming_count == 0 and outgoing_count == 0:
        incoming_outgoing_ratio = 0.0
    elif outgoing_count == 0:
        incoming_outgoing_ratio = float(incoming_count) # Maxed out basically
    else:
        incoming_outgoing_ratio = incoming_count / outgoing_count

    return TransactionFeatures(
        transaction_count=transaction_count,
        avg_transaction_value=avg_transaction_value,
        max_transaction_value=max_transaction_value,
        std_transaction_value=std_transaction_value,
        transaction_frequency=transaction_frequency,
        active_time_span=active_time_span,
        large_transaction_ratio=large_transaction_ratio,
        burst_transaction_activity=burst_transaction_activity,
        incoming_outgoing_ratio=incoming_outgoing_ratio,
    )
