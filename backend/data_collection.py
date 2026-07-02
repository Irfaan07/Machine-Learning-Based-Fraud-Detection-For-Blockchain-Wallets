from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from config import settings


class BlockchainAPIError(Exception):
    pass


async def get_eth_transactions(wallet_address: str) -> list[dict[str, Any]]:
    """
    Fetch recent Ethereum transactions for an address using Etherscan V2 API.
    Returns: [{'value': float, 'timestamp': datetime, 'sender': str, 'receiver': str, 'block_number': int, 'confirmations': int}, ...]
    """
    if not settings.ETHERSCAN_API_KEY:
        raise BlockchainAPIError("ETHERSCAN_API_KEY is not configured.")

    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": 1,
        "module": "account",
        "action": "txlist",
        "address": wallet_address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": settings.MAX_TX_FETCH,
        "sort": "desc",
        "apikey": settings.ETHERSCAN_API_KEY,
    }

    async with httpx.AsyncClient(timeout=settings.API_TIMEOUT_SECONDS) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != "1":
        result = data.get("result", [])
        if not isinstance(result, list):
            err_msg = str(data.get("result")) if data.get("result") else str(data.get("message"))
            raise BlockchainAPIError(f"Etherscan error: {err_msg}")
        return result

    raw_txs = data.get("result", [])
    structured_txs = []

    for tx in raw_txs:
        try:
            value_wei = int(tx.get("value", "0"))
            value_eth = value_wei / 1e18
            ts = int(tx.get("timeStamp"))
            dt = datetime.utcfromtimestamp(ts)
            
            structured_txs.append({
                "value": value_eth,
                "timestamp": dt,
                "sender": tx.get("from", ""),
                "receiver": tx.get("to", ""),
                "block_number": int(tx.get("blockNumber", 0)),
                "confirmations": int(tx.get("confirmations", 0))
            })
        except Exception:
            pass

    return structured_txs


async def get_btc_transactions(wallet_address: str) -> list[dict[str, Any]]:
    """
    Fetch recent Bitcoin transactions for an address using BlockCypher API.
    Returns: [{'value': float, 'timestamp': datetime, 'sender': str, 'receiver': str, 'block_number': int, 'confirmations': int}, ...]
    """
    base_url = f"https://api.blockcypher.com/v1/btc/main/addrs/{wallet_address}/full"
    params: dict[str, Any] = {
        "limit": settings.MAX_TX_FETCH,
    }
    if settings.BLOCKCYPHER_API_TOKEN:
        params["token"] = settings.BLOCKCYPHER_API_TOKEN

    async with httpx.AsyncClient(timeout=settings.API_TIMEOUT_SECONDS) as client:
        resp = await client.get(base_url, params=params)
        if resp.status_code >= 400:
            err_msg = resp.text
            try:
                err_msg = resp.json().get("error", resp.text)
            except Exception:
                pass
            raise BlockchainAPIError(f"BlockCypher error: {err_msg}")
        data = resp.json()

    txs = data.get("txs", [])
    structured_txs = []

    for tx in txs:
        # Sum outputs to this address to get received value
        total_satoshis = 0
        for out in tx.get("outputs", []):
            if wallet_address in out.get("addresses", []):
                total_satoshis += int(out.get("value", 0))

        # Optionally handle sent value if needed, but keeping consistent with original logic:
        # Only counting incoming/involving value as 'transaction value' for this simple feature set, 
        # or we count total exchanged. Let's use total_satoshis for incoming, or sum inputs if sending.
        # To be safe, we just use the max of inputs/outputs to represent the tx magnitude.
        if total_satoshis == 0:
            # Maybe they are the sender
            for inp in tx.get("inputs", []):
                if wallet_address in inp.get("addresses", []):
                    total_satoshis += int(inp.get("output_value", 0))

        if total_satoshis == 0:
            continue

        value_btc = total_satoshis / 1e8
        
        time_str = tx.get("time") or tx.get("received")
        try:
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            dt = datetime.utcnow()

        inputs = tx.get("inputs", [])
        outputs = tx.get("outputs", [])
        
        sender = inputs[0].get("addresses", [""])[0] if inputs and inputs[0].get("addresses") else ""
        receiver = outputs[0].get("addresses", [""])[0] if outputs and outputs[0].get("addresses") else ""

        structured_txs.append({
            "value": value_btc,
            "timestamp": dt,
            "sender": sender,
            "receiver": receiver,
            "block_number": tx.get("block_height", -1),
            "confirmations": tx.get("confirmations", 0)
        })

    return structured_txs
