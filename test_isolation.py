import urllib.request
import json

def api_post(endpoint, data, token=None):
    req = urllib.request.Request(f"http://localhost:8000{endpoint}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read().decode())
    except Exception as e:
        return {"error": str(e)}

def api_get(endpoint, token=None):
    req = urllib.request.Request(f"http://localhost:8000{endpoint}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read().decode())
    except Exception as e:
        return {"error": str(e)}

def test():
    # Register tester2 (tester1 already exists)
    api_post("/auth/register", {"username": "tester2", "email": "tester2@test.com", "password": "password123"})
    
    # Login both
    login1 = api_post("/auth/login", {"email": "tester@test.com", "password": "password123"})
    token1 = login1.get("access_token")
    
    login2 = api_post("/auth/login", {"email": "tester2@test.com", "password": "password123"})
    token2 = login2.get("access_token")
    
    print(f"Tester1 Token OK: {bool(token1)}")
    print(f"Tester2 Token OK: {bool(token2)}")
    
    # Tester1 scans a wallet
    print("Tester1 scanning...")
    scan_res = api_post("/scan-wallet", {"wallet_address": "0x123", "blockchain": "ethereum"}, token1)
    print("Scan ID:", scan_res.get("scan_id") or scan_res.get("error"))
    
    # Verify histories
    hist1 = api_get("/scan-history", token1)
    hist2 = api_get("/scan-history", token2)
    
    scans1 = len(hist1.get("scans", []))
    scans2 = len(hist2.get("scans", []))
    
    print(f"Tester1 history count: {scans1}")
    print(f"Tester2 history count: {scans2}")
    
    if scans1 > 0 and scans2 == 0:
        print("VERIFICATION SUCCESS: History is isolated.")
    else:
        print("VERIFICATION FAILED: Isolation broken.")

if __name__ == "__main__":
    test()
