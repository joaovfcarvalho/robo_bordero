#!/usr/bin/env python3
"""
Simple test script to verify API is working
"""
import requests
import sys

def test_api():
    """Test basic API endpoints"""
    base_url = "http://localhost:8000"

    print("🧪 Testing CBF Borderô Robot API\n")

    # Test 1: Health check
    print("1️⃣  Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

    print()

    # Test 2: Root endpoint
    print("2️⃣  Testing root endpoint...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("   ✅ Root endpoint passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Root endpoint failed: {e}")
        return False

    print()

    # Test 3: Analytics overview (may fail if no data)
    print("3️⃣  Testing analytics overview...")
    try:
        response = requests.get(f"{base_url}/api/analytics/overview", timeout=5)
        if response.status_code == 200:
            print("   ✅ Analytics overview passed")
            data = response.json()
            print(f"   Total matches: {data['general_stats']['total_matches']}")
        elif response.status_code == 500:
            print("   ⚠️  Analytics endpoint accessible but may need data")
        else:
            print(f"   ❌ Analytics overview failed: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Analytics endpoint: {e}")

    print()

    # Test 4: API docs
    print("4️⃣  Testing API documentation...")
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("   ✅ API docs accessible")
            print(f"   Visit: {base_url}/docs")
        else:
            print(f"   ❌ API docs failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ API docs failed: {e}")

    print()
    print("=" * 60)
    print("✅ API is running! You can access:")
    print(f"   - Frontend: http://localhost:3000")
    print(f"   - API: {base_url}")
    print(f"   - API Docs: {base_url}/docs")
    print("=" * 60)

    return True

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
