"""
Test script untuk AI Chat API
Jalankan server terlebih dahulu dengan: python fastapi_app.py
"""
import requests
import json
import time


BASE_URL = "http://localhost:8000"


def print_response(title, response):
    """Pretty print response"""
    print(f"\n{'='*60}")
    print(f"🔹 {title}")
    print(f"{'='*60}")
    print(json.dumps(response, indent=2, ensure_ascii=False))
    print(f"{'='*60}\n")


def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print_response("Health Check", response.json())
    return response.status_code == 200


# def test_ai_status():
#     """Test AI status endpoint"""
#     response = requests.get(f"{BASE_URL}/api/v1/ai/test")
#     print_response("AI Status Check", response.json())
#     return response.status_code == 200


def test_chat(message):
    """Test chat endpoint with a message"""
    print(f"\n📤 Sending message: {message}")
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/api/v1/ai/chat",
        json={"message": message},
        headers={"Content-Type": "application/json"}
    )
    elapsed = time.time() - start_time
    
    result = response.json()
    print_response(f"AI Response (took {elapsed:.2f}s)", result)
    
    return response.status_code == 200


def run_tests():
    """Run all tests"""
    print("\n🚀 Starting AI Chat API Tests")
    print(f"Target: {BASE_URL}")
    print("="*60)
    
    # Test 1: Health Check
    print("\n1️⃣ Testing Health Endpoint...")
    if not test_health():
        print("❌ Health check failed. Is the server running?")
        return
    print("✅ Health check passed!")
    
    # Test 2: AI Status
    # print("\n2️⃣ Testing AI Status Endpoint...")
    # if not test_ai_status():
    #     print("❌ AI status check failed.")
    #     return
    # print("✅ AI status check passed!")
    
    # Test 3: Simple Query
    print("\n3️⃣ Testing Simple Chat Query...")
    if not test_chat("Berapa total produk jeans yang ada?"):
        print("❌ Chat query failed.")
        return
    print("✅ Simple query passed!")
    
    # # Test 4: Brand Query
    # print("\n4️⃣ Testing Brand Filter Query...")
    # if not test_chat("Show me all RALPH LAUREN jeans"):
    #     print("❌ Brand query failed.")
    #     return
    # print("✅ Brand query passed!")
    
    # # Test 5: Discount Query
    # print("\n5️⃣ Testing Discount Query...")
    # if not test_chat("Produk mana yang sedang diskon?"):
    #     print("❌ Discount query failed.")
    #     return
    # print("✅ Discount query passed!")
    
    # # Test 6: Complex Query
    # print("\n6️⃣ Testing Complex Query...")
    # if not test_chat("Berapa rata-rata harga jeans per brand?"):
    #     print("❌ Complex query failed.")
    #     return
    # print("✅ Complex query passed!")
    
    # print("\n" + "="*60)
    # print("🎉 All tests passed successfully!")
    # print("="*60 + "\n")


if __name__ == "__main__":
    try:
        run_tests()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to server!")
        print("Please make sure the server is running:")
        print("  python fastapi_app.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
