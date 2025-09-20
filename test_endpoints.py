"""
Simple test script to verify MCP HTTP Server endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8001"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    print("\n🔍 Testing root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
        return False

def test_query_post():
    """Test POST query endpoint"""
    print("\n🔍 Testing POST query endpoint...")
    try:
        payload = {
            "query": "Hello, this is a test query",
            "user_id": "test-user-123",
            "max_steps": 5
        }
        response = requests.post(
            f"{BASE_URL}/query",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ POST query failed: {e}")
        return False

def test_query_get():
    """Test GET query endpoint"""
    print("\n🔍 Testing GET query endpoint...")
    try:
        params = {
            "query": "Hello, this is a test query",
            "user_id": "test-user-123",
            "max_steps": 5
        }
        response = requests.get(f"{BASE_URL}/query", params=params)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ GET query failed: {e}")
        return False

def test_streaming_endpoint():
    """Test streaming endpoint"""
    print("\n🔍 Testing streaming endpoint...")
    try:
        params = {
            "query": "Hello, this is a test streaming query",
            "user_id": "test-user-123",
            "max_steps": 3
        }
        
        print("Making streaming request...")
        response = requests.get(
            f"{BASE_URL}/query/stream", 
            params=params,
            stream=True
        )
        
        print(f"Status: {response.status_code}")
        print("Streaming response:")
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data = line_str[6:]  # Remove 'data: ' prefix
                    try:
                        json_data = json.loads(data)
                        print(f"  {json.dumps(json_data, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"  Raw data: {data}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Streaming query failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 MCP HTTP Server Endpoint Tests")
    print("=" * 50)
    
    # Wait a moment for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    tests = [
        ("Health Check", test_health_check),
        ("Root Endpoint", test_root_endpoint),
        ("POST Query", test_query_post),
        ("GET Query", test_query_get),
        ("Streaming Query", test_streaming_endpoint),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
            print(f"✅ {test_name}: {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Server is working correctly.")
    else:
        print("⚠️  Some tests failed. Check server logs and configuration.")

if __name__ == "__main__":
    main()
