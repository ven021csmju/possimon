import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def login():
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return None
    # Check if token is in cookies or body
    # Based on main.py, it uses SessionMiddleware but auth/jwt.py might handle cookies
    # Let's check how auth/login works
    return resp.json().get("access_token")

def create_order(token):
    headers = {"Authorization": f"Bearer {token}"}
    order_data = {
        "order_type": "online",
        "payment_method": "cash",
        "shipping_method": "standard",
        "address_id": 1,
        "is_full_tax_invoice": True,
        "tax_id": "1234567890123",
        "tax_business_name": "Test Co",
        "use_shipping_as_tax_address": True,
        "items": [
            {"product_id": 1, "quantity": 1}
        ]
    }
    resp = requests.post(f"{BASE_URL}/api/orders", json=order_data, headers=headers)
    print(f"Order creation status: {resp.status_code}")
    print(f"Order creation response: {resp.text}")

if __name__ == "__main__":
    # Note: Backend must be running
    token = login()
    if token:
        create_order(token)
