import urllib.request
import json

def test():
    req = urllib.request.Request("http://localhost:8000/auth/register",
        data=json.dumps({"username":"tester","email":"tester@test.com","password":"password123"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        print("Register OK")
    except Exception as e:
        print("Register Error:", str(e))
        
    req2 = urllib.request.Request("http://localhost:8000/auth/login",
        data=json.dumps({"email":"tester@test.com","password":"password123"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        res = urllib.request.urlopen(req2)
        print("Login OK:", res.read().decode())
    except Exception as e:
        print("Login Error:", str(e))

test()
