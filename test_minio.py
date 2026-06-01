import requests
import os

BASE_URL = "http://localhost:8000"

def test_health():
    response = requests.get(f"{BASE_URL}/")
    print(f"Health Check: {response.json()}")

def test_upload_review_image():
    print("\n--- Testing Review Image Upload ---")
    # Create a dummy image file
    with open("test_image.jpg", "wb") as f:
        f.write(b"fake image data")
    
    with open("test_image.jpg", "rb") as f:
        files = {"file": ("test_image.jpg", f, "image/jpeg")}
        response = requests.post(f"{BASE_URL}/reviews/media", files=files)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if os.path.exists("test_image.jpg"):
        os.remove("test_image.jpg")

def test_upload_review_video():
    print("\n--- Testing Review Video Upload ---")
    # Create a dummy video file
    with open("test_video.mp4", "wb") as f:
        f.write(b"fake video data")
    
    with open("test_video.mp4", "rb") as f:
        files = {"file": ("test_video.mp4", f, "video/mp4")}
        response = requests.post(f"{BASE_URL}/reviews/media", files=files)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if os.path.exists("test_video.mp4"):
        os.remove("test_video.mp4")

if __name__ == "__main__":
    try:
        test_health()
        test_upload_review_image()
        test_upload_review_video()
    except Exception as e:
        print(f"Error: {e}")
