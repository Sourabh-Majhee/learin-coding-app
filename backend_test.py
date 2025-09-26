#!/usr/bin/env python3
"""
Backend API Testing Suite for Code Learning Platform
Tests authentication, AI integration, and core functionality
"""

import requests
import json
import os
import sys
from datetime import datetime
import time

# Get backend URL from frontend .env file
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('EXPO_PUBLIC_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except FileNotFoundError:
        pass
    return "http://localhost:8001"  # fallback

BASE_URL = get_backend_url()
API_URL = f"{BASE_URL}/api"

print(f"Testing backend at: {API_URL}")

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def log_pass(self, test_name):
        self.passed += 1
        print(f"✅ PASS: {test_name}")
        
    def log_fail(self, test_name, error):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"❌ FAIL: {test_name} - {error}")
        
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {self.passed}/{total} tests passed")
        if self.errors:
            print(f"\nFAILED TESTS:")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*60}")
        return self.failed == 0

# Global test results
results = TestResults()

def test_health_endpoints():
    """Test basic health check endpoints"""
    print("\n🔍 Testing Health Check Endpoints...")
    
    # Test root endpoint
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "message" in data and "status" in data:
                results.log_pass("Root endpoint (/api/)")
            else:
                results.log_fail("Root endpoint (/api/)", f"Invalid response format: {data}")
        else:
            results.log_fail("Root endpoint (/api/)", f"Status code: {response.status_code}")
    except Exception as e:
        results.log_fail("Root endpoint (/api/)", str(e))
    
    # Test health endpoint
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "status" in data and data["status"] == "healthy":
                results.log_pass("Health endpoint (/api/health)")
            else:
                results.log_fail("Health endpoint (/api/health)", f"Invalid response: {data}")
        else:
            results.log_fail("Health endpoint (/api/health)", f"Status code: {response.status_code}")
    except Exception as e:
        results.log_fail("Health endpoint (/api/health)", str(e))

def test_user_registration():
    """Test user registration endpoint"""
    print("\n🔍 Testing User Registration...")
    
    # Test valid registration
    user_data = {
        "email": "sarah.developer@example.com",
        "username": "sarah_codes",
        "password": "SecurePass123!",
        "preferred_languages": ["python", "javascript"],
        "skill_level": "intermediate",
        "explanation_language": "english"
    }
    
    try:
        response = requests.post(f"{API_URL}/auth/register", json=user_data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "token_type" in data:
                results.log_pass("User registration with valid data")
                return data["access_token"]  # Return token for further tests
            else:
                results.log_fail("User registration", f"Invalid response format: {data}")
        else:
            results.log_fail("User registration", f"Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        results.log_fail("User registration", str(e))
    
    # Test duplicate email registration
    try:
        response = requests.post(f"{API_URL}/auth/register", json=user_data, timeout=10)
        if response.status_code == 400:
            results.log_pass("Duplicate email registration rejection")
        else:
            results.log_fail("Duplicate email registration", f"Expected 400, got {response.status_code}")
    except Exception as e:
        results.log_fail("Duplicate email registration", str(e))
    
    # Test invalid registration (missing fields)
    invalid_data = {"email": "test@example.com"}
    try:
        response = requests.post(f"{API_URL}/auth/register", json=invalid_data, timeout=10)
        if response.status_code in [400, 422]:  # FastAPI returns 422 for validation errors
            results.log_pass("Invalid registration data rejection")
        else:
            results.log_fail("Invalid registration data", f"Expected 400/422, got {response.status_code}")
    except Exception as e:
        results.log_fail("Invalid registration data", str(e))
    
    return None

def test_user_login(token=None):
    """Test user login endpoint"""
    print("\n🔍 Testing User Login...")
    
    # Test valid login
    login_data = {
        "email": "sarah.developer@example.com",
        "password": "SecurePass123!"
    }
    
    try:
        response = requests.post(f"{API_URL}/auth/login", json=login_data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "token_type" in data:
                results.log_pass("User login with valid credentials")
                return data["access_token"]
            else:
                results.log_fail("User login", f"Invalid response format: {data}")
        else:
            results.log_fail("User login", f"Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        results.log_fail("User login", str(e))
    
    # Test invalid login
    invalid_login = {
        "email": "sarah.developer@example.com",
        "password": "WrongPassword"
    }
    
    try:
        response = requests.post(f"{API_URL}/auth/login", json=invalid_login, timeout=10)
        if response.status_code == 401:
            results.log_pass("Invalid login credentials rejection")
        else:
            results.log_fail("Invalid login", f"Expected 401, got {response.status_code}")
    except Exception as e:
        results.log_fail("Invalid login", str(e))
    
    return token

def test_protected_route(token):
    """Test protected route with JWT token"""
    print("\n🔍 Testing Protected Route (/api/auth/me)...")
    
    if not token:
        results.log_fail("Protected route test", "No valid token available")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{API_URL}/auth/me", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "email" in data and "username" in data:
                results.log_pass("Protected route with valid token")
            else:
                results.log_fail("Protected route", f"Invalid user data: {data}")
        else:
            results.log_fail("Protected route", f"Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        results.log_fail("Protected route", str(e))
    
    # Test without token
    try:
        response = requests.get(f"{API_URL}/auth/me", timeout=10)
        if response.status_code == 403:  # FastAPI HTTPBearer returns 403
            results.log_pass("Protected route without token rejection")
        else:
            results.log_fail("Protected route without token", f"Expected 403, got {response.status_code}")
    except Exception as e:
        results.log_fail("Protected route without token", str(e))

def test_code_explanation_api(token):
    """Test code explanation API with Gemini integration"""
    print("\n🔍 Testing Code Explanation API...")
    
    if not token:
        results.log_fail("Code explanation test", "No valid token available")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test full code explanation
    code_request = {
        "code": """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))""",
        "language": "python",
        "explanation_level": "beginner"
    }
    
    try:
        response = requests.post(f"{API_URL}/code/explain", json=code_request, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "explanation" in data and "short_explanation" in data and "confidence_score" in data:
                results.log_pass("Code explanation - full code (beginner level)")
                print(f"   Short explanation: {data['short_explanation'][:100]}...")
            else:
                results.log_fail("Code explanation", f"Invalid response format: {data}")
        else:
            results.log_fail("Code explanation", f"Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        results.log_fail("Code explanation", str(e))
    
    # Test line-by-line explanation
    line_request = {
        "code": """def calculate_area(radius):
    pi = 3.14159
    area = pi * radius ** 2
    return area""",
        "language": "python",
        "line_number": 3,
        "explanation_level": "intermediate"
    }
    
    try:
        response = requests.post(f"{API_URL}/code/explain", json=line_request, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "explanation" in data:
                results.log_pass("Code explanation - line-by-line (intermediate level)")
            else:
                results.log_fail("Line explanation", f"Invalid response format: {data}")
        else:
            results.log_fail("Line explanation", f"Status code: {response.status_code}")
    except Exception as e:
        results.log_fail("Line explanation", str(e))
    
    # Test advanced level explanation
    advanced_request = {
        "code": """class BinarySearchTree:
    def __init__(self):
        self.root = None
    
    def insert(self, value):
        if not self.root:
            self.root = TreeNode(value)
        else:
            self._insert_recursive(self.root, value)""",
        "language": "python",
        "explanation_level": "advanced"
    }
    
    try:
        response = requests.post(f"{API_URL}/code/explain", json=advanced_request, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "explanation" in data:
                results.log_pass("Code explanation - advanced level")
            else:
                results.log_fail("Advanced explanation", f"Invalid response format: {data}")
        else:
            results.log_fail("Advanced explanation", f"Status code: {response.status_code}")
    except Exception as e:
        results.log_fail("Advanced explanation", str(e))

def test_dashboard_stats_api(token):
    """Test dashboard stats API"""
    print("\n🔍 Testing Dashboard Stats API...")
    
    if not token:
        results.log_fail("Dashboard stats test", "No valid token available")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{API_URL}/dashboard/stats", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            required_keys = ["user", "activity", "progress"]
            if all(key in data for key in required_keys):
                # Check user data structure
                user_data = data["user"]
                if "username" in user_data and "total_xp" in user_data:
                    results.log_pass("Dashboard stats API - data structure")
                else:
                    results.log_fail("Dashboard stats", f"Invalid user data structure: {user_data}")
            else:
                results.log_fail("Dashboard stats", f"Missing required keys. Got: {list(data.keys())}")
        else:
            results.log_fail("Dashboard stats", f"Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        results.log_fail("Dashboard stats", str(e))

def test_cors_configuration():
    """Test CORS configuration"""
    print("\n🔍 Testing CORS Configuration...")
    
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,Authorization"
    }
    
    try:
        response = requests.options(f"{API_URL}/auth/login", headers=headers, timeout=10)
        if response.status_code in [200, 204]:
            cors_headers = response.headers
            if "Access-Control-Allow-Origin" in cors_headers:
                results.log_pass("CORS configuration")
            else:
                results.log_fail("CORS configuration", "Missing CORS headers")
        else:
            results.log_fail("CORS configuration", f"OPTIONS request failed: {response.status_code}")
    except Exception as e:
        results.log_fail("CORS configuration", str(e))

def main():
    """Run all backend tests"""
    print("🚀 Starting Code Learning Platform Backend API Tests")
    print(f"Backend URL: {API_URL}")
    print("="*60)
    
    # Test health endpoints first
    test_health_endpoints()
    
    # Test authentication flow
    token = test_user_registration()
    token = test_user_login(token)
    test_protected_route(token)
    
    # Test core functionality with authenticated user
    if token:
        test_code_explanation_api(token)
        test_dashboard_stats_api(token)
    else:
        print("⚠️  Skipping authenticated tests - no valid token")
    
    # Test CORS
    test_cors_configuration()
    
    # Print final results
    success = results.summary()
    
    if success:
        print("\n🎉 All backend tests passed!")
        sys.exit(0)
    else:
        print(f"\n💥 {results.failed} tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()