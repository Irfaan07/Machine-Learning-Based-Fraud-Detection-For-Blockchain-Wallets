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

def test_al():
    token = get_token()
    if not token:
        print("Failed to get token for tester@test.com. Create it first.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Scan a fake wallet
    scan_res = httpx.post(f"{API_URL}/scan-wallet", json={"wallet_address": "flaggingTest", "blockchain": "bitcoin"}, headers=headers, timeout=20.0)
    scan_data = scan_res.json()
    scan_id = scan_data["scan_id"]
    print(f"Scanned wallet, got ID {scan_id}")
    
    # 2. Flag it
    flag_res = httpx.post(f"{API_URL}/flag-scan/{scan_id}", json={"feedback": 1}, headers=headers, timeout=10.0)
    print(f"Flagged output: {flag_res.json()}")
    
    # 3. Trigger Retrain
    print("Triggering /retrain endpoint... Please wait a few seconds.")
    start = time.time()
    retrain_res = httpx.post(f"{API_URL}/retrain", headers=headers, timeout=120.0)
    diff = time.time() - start
    print(f"Retrain output ({diff:.1f}s): {retrain_res.json()}")
    
if __name__ == "__main__":
    test_al()
