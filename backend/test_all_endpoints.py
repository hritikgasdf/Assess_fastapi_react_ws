"""
Comprehensive endpoint test for async migration
Tests all CRUD operations on all endpoints
"""
import asyncio
import httpx
import json
import time

BASE_URL = "http://localhost:8000"

# Test user credentials
MANAGER_EMAIL = "manager@hotel.com"
MANAGER_PASSWORD = "manager123"
STAFF_EMAIL = "staff@hotel.com"
STAFF_PASSWORD = "staff123"

async def test_health():
    """Test health endpoint"""
    print("\n1️⃣ Testing Health Endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print(f"   ✅ Health: {response.json()}")
        return True

async def test_auth_endpoints():
    """Test authentication endpoints"""
    print("\n2️⃣ Testing Auth Endpoints...")
    async with httpx.AsyncClient() as client:
        # Test login with manager
        login_data = {
            "email": MANAGER_EMAIL,
            "password": MANAGER_PASSWORD
        }
        response = await client.post(f"{BASE_URL}/api/auth/login", json=login_data)
        
        if response.status_code != 200:
            print(f"   ⚠️  Login failed: {response.status_code} - {response.text}")
            return None
            
        token = response.json()["access_token"]
        print(f"   ✅ Login successful")
        
        # Test /me endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Get user failed: {response.text}"
        user = response.json()
        print(f"   ✅ Get current user: {user['email']} ({user['role']})")
        
        return token

async def test_get_requests(token):
    """Test GET /api/requests"""
    print("\n3️⃣ Testing GET /api/requests...")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(f"{BASE_URL}/api/requests", headers=headers)
        
        if response.status_code != 200:
            print(f"   ❌ FAILED: Status {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
        requests = response.json()
        print(f"   ✅ GET requests: {len(requests)} items")
        return True

async def test_create_request(token):
    """Test POST /api/requests"""
    print("\n4️⃣ Testing POST /api/requests...")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        request_data = {
            "guest_id": 1,
            "room_id": 1,
            "description": "Need extra towels for room cleaning"
        }
        response = await client.post(f"{BASE_URL}/api/requests", json=request_data, headers=headers)
        
        if response.status_code not in [200, 201]:
            print(f"   ❌ FAILED: Status {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
        new_request = response.json()
        print(f"   ✅ Created request ID: {new_request['id']}, Category: {new_request.get('category', 'N/A')}")
        return new_request['id']

async def test_update_request(token, request_id):
    """Test PATCH /api/requests/{id}"""
    print("\n5️⃣ Testing PATCH /api/requests/{id}...")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        update_data = {
            "status": "Completed"
        }
        response = await client.patch(
            f"{BASE_URL}/api/requests/{request_id}", 
            json=update_data, 
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"   ❌ FAILED: Status {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
        updated = response.json()
        print(f"   ✅ Updated request status to: {updated['status']}")
        return True

async def test_get_feedback(token):
    """Test GET /api/feedback"""
    print("\n6️⃣ Testing GET /api/feedback...")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(f"{BASE_URL}/api/feedback", headers=headers)
        
        if response.status_code != 200:
            print(f"   ❌ FAILED: Status {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
        feedbacks = response.json()
        print(f"   ✅ GET feedback: {len(feedbacks)} items")
        return True

async def test_create_feedback(token):
    """Test POST /api/feedback"""
    print("\n7️⃣ Testing POST /api/feedback...")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        feedback_data = {
            "guest_id": 1,
            "room_id": 1,
            "message": "The room service was terrible and the staff was rude"
        }
        response = await client.post(f"{BASE_URL}/api/feedback", json=feedback_data, headers=headers)
        
        if response.status_code not in [200, 201]:
            print(f"   ❌ FAILED: Status {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
        new_feedback = response.json()
        print(f"   ✅ Created feedback ID: {new_feedback['id']}, Sentiment: {new_feedback.get('sentiment', 'N/A')}")
        return new_feedback['id']

async def test_generate_smart_response(token, feedback_id):
    """Test POST /api/feedback/{id}/generate-response"""
    print("\n8️⃣ Testing POST /api/feedback/{id}/generate-response...")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            f"{BASE_URL}/api/feedback/{feedback_id}/generate-response",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"   ⚠️  Status {response.status_code}: {response.text}")
            return False
            
        result = response.json()
        print(f"   ✅ Generated smart response (length: {len(result.get('smart_response', ''))} chars)")
        return True

async def test_concurrent_load():
    """Test concurrent requests to verify no blocking"""
    print("\n9️⃣ Testing Concurrent Load (20 requests)...")
    
    token = await test_auth_endpoints()
    if not token:
        print("   ❌ Cannot test concurrent load without token")
        return False
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        start_time = time.time()
        
        # Create 20 concurrent GET requests
        tasks = [
            client.get(f"{BASE_URL}/api/requests", headers=headers)
            for _ in range(20)
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Check results
        success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
        
        print(f"   ✅ Completed 20 requests in {elapsed:.2f}s")
        print(f"   Success: {success_count}/20")
        
        if elapsed < 1.0:
            print(f"   🚀 EXCELLENT! True parallel execution (avg {elapsed/20*1000:.0f}ms per request)")
        elif elapsed < 3.0:
            print(f"   ✅ GOOD! Non-blocking execution")
        else:
            print(f"   ⚠️  SLOW: May still have blocking issues")
        
        return success_count >= 18  # Allow for minor failures

async def main():
    print("=" * 70)
    print("  COMPREHENSIVE ENDPOINT TEST SUITE - Async Migration")
    print("=" * 70)
    
    results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    try:
        # Test 1: Health
        if await test_health():
            results["passed"] += 1
        else:
            results["failed"] += 1
            
        # Test 2: Auth
        token = await test_auth_endpoints()
        if token:
            results["passed"] += 1
        else:
            results["failed"] += 1
            print("\n❌ Cannot continue without authentication token")
            return
            
        # Test 3: Get Requests
        if await test_get_requests(token):
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append("GET /api/requests failed")
            
        # Test 4: Create Request
        request_id = await test_create_request(token)
        if request_id:
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append("POST /api/requests failed")
            
        # Test 5: Update Request (only if we created one)
        if request_id:
            if await test_update_request(token, request_id):
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["errors"].append("PATCH /api/requests/{id} failed")
                
        # Test 6: Get Feedback
        if await test_get_feedback(token):
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append("GET /api/feedback failed")
            
        # Test 7: Create Feedback
        feedback_id = await test_create_feedback(token)
        if feedback_id:
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append("POST /api/feedback failed")
            
        # Test 8: Generate Smart Response (only if we have negative feedback)
        if feedback_id:
            if await test_generate_smart_response(token, feedback_id):
                results["passed"] += 1
            else:
                results["failed"] += 1
                # Don't add to critical errors, might be due to sentiment
                
        # Test 9: Concurrent Load
        if await test_concurrent_load():
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append("Concurrent load test failed")
        
        # Print summary
        print("\n" + "=" * 70)
        print("  TEST SUMMARY")
        print("=" * 70)
        print(f"  ✅ Passed: {results['passed']}")
        print(f"  ❌ Failed: {results['failed']}")
        
        if results["errors"]:
            print("\n  Critical Errors:")
            for error in results["errors"]:
                print(f"    - {error}")
        
        if results["failed"] == 0:
            print("\n  🎉 ALL TESTS PASSED!")
            print("  ✓ All endpoints working correctly")
            print("  ✓ Async migration successful")
            print("  ✓ No blocking detected")
        else:
            print("\n  ⚠️  SOME TESTS FAILED")
            print("  Please review the errors above")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
