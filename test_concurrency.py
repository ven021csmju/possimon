import threading
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def create_test_data():
    # 1. Create a product with 5 stock
    product_data = {
        "name": "Concurrency Test Product",
        "price": 100.0,
        "stock": 5
    }
    resp = requests.post(f"{BASE_URL}/products", json=product_data)
    print(f"Product creation status: {resp.status_code}")
    print(f"Product creation response: {resp.text}")
    product = resp.json()
    return product['id']

def place_order(user_id, product_id, quantity, results):
    order_data = {
        "user_id": user_id,
        "address_id": 1, # Assume address 1 exists from seed
        "payment_method": "credit_card",
        "items": [
            {"product_id": product_id, "quantity": quantity}
        ]
    }
    try:
        resp = requests.post(f"{BASE_URL}/orders", json=order_data)
        results.append(resp.status_code)
    except Exception as e:
        results.append(str(e))

def run_test():
    product_id = create_test_data()
    
    threads = []
    results = []
    
    # Try to place 10 orders of 1 item each (total 10 items, but only 5 in stock)
    print("Launching 10 concurrent orders...")
    for i in range(10):
        t = threading.Thread(target=place_order, args=(1, product_id, 1, results))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    success_count = results.count(200)
    fail_count = results.count(400)
    
    print(f"\nTest Results:")
    print(f"Total requests: {len(results)}")
    print(f"Successful orders: {success_count}")
    print(f"Failed orders (400 Insufficient Stock): {fail_count}")
    
    # Check final stock
    resp = requests.get(f"{BASE_URL}/products")
    products = resp.json()
    for p in products:
        if p['id'] == product_id:
            print(f"Final stock: {p['stock']}")
            if p['stock'] >= 0 and success_count == 5:
                print("SUCCESS: Concurrency handled correctly!")
            else:
                print("FAILURE: Stock inconsistency detected!")

if __name__ == "__main__":
    # Ensure server is running before this
    run_test()
