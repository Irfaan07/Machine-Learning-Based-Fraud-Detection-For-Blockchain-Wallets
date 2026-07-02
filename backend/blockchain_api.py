from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from config import settings


class BlockchainAPIError(Exception):
    pass


async def fetch_ethereum_transactions(address: str) -> list[dict[str, Any]]:
    """
    Fetch recent Ethereum transactions for an address using Etherscan API.
    Returns a list of transactions with at least 'value' and 'timeStamp'.
    """
    if not settings.ETHERSCAN_API_KEY:
        raise BlockchainAPIError("ETHERSCAN_API_KEY is not configured.")

    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": 1,
        "module": "account",
        "action": "txlist",
        "address": address,
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
        # Etherscan returns status "0" for no transactions as well
        result = data.get("result", [])
        if not isinstance(result, list):
            err_msg = str(data.get("result")) if data.get("result") else str(data.get("message"))
            raise BlockchainAPIError(f"Etherscan error: {err_msg}")
        return result

    return data.get("result", [])


async def fetch_bitcoin_transactions(address: str) -> list[dict[str, Any]]:
    """
    Fetch recent Bitcoin transactions for an address using BlockCypher API.
    Returns a list of simplified tx dicts with 'value' (in BTC) and 'received' timestamp.
    """
    base_url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}/full"
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
    simplified: list[dict[str, Any]] = []
    for tx in txs:
        # Sum outputs to this address
        total_satoshis = 0
        for out in tx.get("outputs", []):
            if address in out.get("addresses", []):
                total_satoshis += int(out.get("value", 0))

        if total_satoshis == 0:
            continue

        # Convert satoshi to BTC
        value_btc = total_satoshis / 1e8
        received = tx.get("received") or tx.get("confirmed")

        simplified.append(
            {
                "value": value_btc,
                "time": received,
            }
        )

    return simplified


def parse_ethereum_tx(tx: dict[str, Any]) -> tuple[float, datetime] | None:
    try:
        value_wei = int(tx.get("value", "0"))
        if value_wei <= 0:
            return None
        value_eth = value_wei / 1e18
        ts = int(tx.get("timeStamp"))
        dt = datetime.utcfromtimestamp(ts)
        return value_eth, dt
    except Exception:
        return None


def parse_bitcoin_tx(tx: dict[str, Any]) -> tuple[float, datetime] | None:
    try:
        value_btc = float(tx.get("value", 0.0))
        if value_btc <= 0:
            return None
        time_str = tx.get("time") or tx.get("received")
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return value_btc, dt
    except Exception:
        return None

