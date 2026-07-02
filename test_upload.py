import time
import httpx

API_URL = "http://localhost:8000"

def get_token():
    res = httpx.post(
        f"{API_URL}/token",
        data={"username": "tester@test.com", "password": "password123"}
    )
    if res.status_code == 200:
        return res.json().get("access_token")
    return None

def test_batch():
    token = get_token()
    if not token:
        print("Failed to get token.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    with open("test_batch.csv", "rb") as f:
        files = {"file": ("test_batch.csv", f, "text/csv")}
        res = httpx.post(f"{API_URL}/scan-batch", headers=headers, files=files, timeout=60.0)
    
    if res.status_code == 200:
        results = res.json()
        print(f"Batch success! Scanned {len(results)} wallets.")
        for r in results:
            print(f"- {r['wallet_address']}: {r['risk_level']} (ID: {r['scan_id']})")
    else:
        print(f"Batch failed! {res.status_code}: {res.text}")

if __name__ == "__main__":
    test_batch()
