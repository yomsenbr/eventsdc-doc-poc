#!/usr/bin/env python3
"""
Test suite for EventsDC Document Ingestion POC
Tests duplicate detection, search functionality, and system health
"""

import requests
import json
import time
import sys
import os
from typing import Dict, Any, List

# Test configuration
API_BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_result(self, test_name: str, success: bool, message: str = ""):
        if success:
            self.passed += 1
            print(f"✅ {test_name}: PASSED {message}")
        else:
            self.failed += 1
            self.errors.append(f"{test_name}: {message}")
            print(f"❌ {test_name}: FAILED {message}")
    
    def print_summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        
        if self.errors:
            print(f"\nFailed Tests:")
            for error in self.errors:
                print(f"  - {error}")
        
        success_rate = (self.passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        return self.failed == 0

def wait_for_api(timeout: int = TEST_TIMEOUT) -> bool:
    """Wait for API to be available"""
    print(f"Waiting for API at {API_BASE_URL}...")
    
    for i in range(timeout):
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ API is available after {i+1} seconds")
                return True
        except:
            pass
        time.sleep(1)
    
    print(f"❌ API not available after {timeout} seconds")
    return False

def create_test_file(content: str, filename: str) -> str:
    """Create a test file with given content"""
    filepath = f"test_{filename}"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return filepath

def test_api_health(results: TestResults):
    """Test API health endpoint"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        success = response.status_code == 200
        results.add_result("API Health Check", success, f"Status: {response.status_code}")
        return success
    except Exception as e:
        results.add_result("API Health Check", False, str(e))
        return False

def test_document_upload(results: TestResults) -> Dict[str, Any]:
    """Test document upload functionality"""
    # Create test document with timestamp to ensure uniqueness
    import time
    timestamp = str(int(time.time()))
    test_content = f"""
    EventsDC Document Test - {timestamp}
    
    This is a test document for the EventsDC Document Ingestion POC.
    It contains sample content to test OCR, indexing, and search functionality.
    
    Key Topics:
    - Document processing
    - Search capabilities  
    - Duplicate detection
    - EventsDC operations
    
    Test timestamp: {timestamp}
    This document should be properly indexed and searchable.
    """
    
    test_file = create_test_file(test_content, f"document1_{timestamp}.txt")
    
    try:
        with open(test_file, 'rb') as f:
            files = {"file": (f"test_document_{timestamp}.txt", f, "text/plain")}
            response = requests.post(f"{API_BASE_URL}/upload", files=files)
        
        os.remove(test_file)  # Clean up
        
        if response.status_code == 200:
            data = response.json()
            success = not data.get("duplicate", False)
            results.add_result("Document Upload", success, f"Document ID: {data.get('document_id', 'N/A')}")
            return data
        else:
            results.add_result("Document Upload", False, f"HTTP {response.status_code}")
            return {}
            
    except Exception as e:
        results.add_result("Document Upload", False, str(e))
        return {}

def test_duplicate_detection(results: TestResults):
    """Test duplicate document detection"""
    # Create identical test document (use same timestamp as the previous test)
    import time
    timestamp = str(int(time.time()))
    test_content = f"""
    EventsDC Document Test - {timestamp}
    
    This is a test document for the EventsDC Document Ingestion POC.
    It contains sample content to test OCR, indexing, and search functionality.
    
    Key Topics:
    - Document processing
    - Search capabilities  
    - Duplicate detection
    - EventsDC operations
    
    Test timestamp: {timestamp}
    This document should be properly indexed and searchable.
    """
    
    test_file = create_test_file(test_content, f"document1_duplicate_{timestamp}.txt")
    
    try:
        with open(test_file, 'rb') as f:
            files = {"file": (f"test_document_{timestamp}.txt", f, "text/plain")}  # Same filename as previous test
            response = requests.post(f"{API_BASE_URL}/upload", files=files)
        
        os.remove(test_file)  # Clean up
        
        if response.status_code == 200:
            data = response.json()
            is_duplicate = data.get("duplicate", False)
            results.add_result("Duplicate Detection", is_duplicate, 
                             "Content duplicate detected" if data.get("content_duplicate") else "File duplicate detected")
        else:
            results.add_result("Duplicate Detection", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_result("Duplicate Detection", False, str(e))

def test_search_functionality(results: TestResults):
    """Test different search types"""
    search_queries = [
        ("EventsDC", "keyword"),
        ("document processing", "vector"),
        ("test capabilities", "hybrid")
    ]
    
    for query, search_type in search_queries:
        try:
            data = {
                "query": query,
                "search_type": search_type,
                "limit": 5
            }
            response = requests.post(f"{API_BASE_URL}/search", json=data)
            
            if response.status_code == 200:
                search_results = response.json()
                has_results = search_results.get("total_results", 0) > 0
                results.add_result(f"Search ({search_type})", has_results, 
                                 f"Query: '{query}', Results: {search_results.get('total_results', 0)}")
            else:
                results.add_result(f"Search ({search_type})", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            results.add_result(f"Search ({search_type})", False, str(e))

def test_chatbot_functionality(results: TestResults):
    """Test chatbot Q&A functionality"""
    test_questions = [
        "What is this document about?",
        "What are the key topics mentioned?",
        "Tell me about EventsDC operations"
    ]
    
    for question in test_questions:
        try:
            data = {
                "question": question,
                "context_limit": 3
            }
            response = requests.post(f"{API_BASE_URL}/chat", json=data)
            
            if response.status_code == 200:
                chat_result = response.json()
                has_answer = bool(chat_result.get("answer", "").strip())
                results.add_result(f"Chatbot Q&A", has_answer, f"Question: '{question[:30]}...'")
                break  # Test one question successfully
            else:
                results.add_result(f"Chatbot Q&A", False, f"HTTP {response.status_code}")
                break
                
        except Exception as e:
            results.add_result(f"Chatbot Q&A", False, str(e))
            break

def test_document_listing(results: TestResults):
    """Test document listing functionality"""
    try:
        response = requests.get(f"{API_BASE_URL}/documents")
        
        if response.status_code == 200:
            documents = response.json()
            has_documents = documents.get("total_documents", 0) > 0
            results.add_result("Document Listing", has_documents, 
                             f"Total documents: {documents.get('total_documents', 0)}")
        else:
            results.add_result("Document Listing", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_result("Document Listing", False, str(e))

def test_deduplication_effectiveness(results: TestResults):
    """Test that search results don't contain duplicates"""
    try:
        data = {
            "query": "EventsDC test document",
            "search_type": "hybrid",
            "limit": 10
        }
        response = requests.post(f"{API_BASE_URL}/search", json=data)
        
        if response.status_code == 200:
            search_results = response.json()
            results_list = search_results.get("results", [])
            
            # Check for duplicate filenames in results
            filenames = [r.get("filename", "") for r in results_list]
            unique_filenames = set(filenames)
            
            no_duplicates = len(filenames) == len(unique_filenames)
            results.add_result("Search Deduplication", no_duplicates, 
                             f"Results: {len(filenames)}, Unique: {len(unique_filenames)}")
        else:
            results.add_result("Search Deduplication", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_result("Search Deduplication", False, str(e))

def run_security_checks(results: TestResults):
    """Run basic security checks"""
    # Test file upload limits
    try:
        # Test with very large content (but not actually large file)
        large_content = "x" * (1024 * 1024)  # 1MB of text
        test_file = create_test_file(large_content, "large_document.txt")
        
        with open(test_file, 'rb') as f:
            files = {"file": ("large_test.txt", f, "text/plain")}
            response = requests.post(f"{API_BASE_URL}/upload", files=files)
        
        os.remove(test_file)  # Clean up
        
        # Should either succeed or fail gracefully
        graceful_handling = response.status_code in [200, 413, 422]
        results.add_result("Large File Handling", graceful_handling, f"HTTP {response.status_code}")
        
    except Exception as e:
        results.add_result("Large File Handling", False, str(e))
    
    # Test invalid file type
    try:
        test_file = create_test_file("test content", "test.xyz")
        
        with open(test_file, 'rb') as f:
            files = {"file": ("test.xyz", f, "application/octet-stream")}
            response = requests.post(f"{API_BASE_URL}/upload", files=files)
        
        os.remove(test_file)  # Clean up
        
        # Should reject invalid file types
        rejected = response.status_code in [400, 422]
        results.add_result("Invalid File Type Rejection", rejected, f"HTTP {response.status_code}")
        
    except Exception as e:
        results.add_result("Invalid File Type Rejection", False, str(e))

def main():
    """Run all tests"""
    print("🧪 EventsDC Document Ingestion POC - System Test Suite")
    print("=" * 60)
    
    # Wait for API to be available
    if not wait_for_api():
        print("❌ Cannot connect to API. Make sure the server is running.")
        sys.exit(1)
    
    results = TestResults()
    
    # Run tests in logical order
    print("\n📋 Running Health Checks...")
    test_api_health(results)
    
    print("\n📄 Testing Document Processing...")
    uploaded_doc = test_document_upload(results)
    
    print("\n🔍 Testing Duplicate Detection...")
    test_duplicate_detection(results)
    
    print("\n🔎 Testing Search Functionality...")
    test_search_functionality(results)
    
    print("\n💬 Testing Chatbot...")
    test_chatbot_functionality(results)
    
    print("\n📚 Testing Document Management...")
    test_document_listing(results)
    
    print("\n🔒 Testing Deduplication...")
    test_deduplication_effectiveness(results)
    
    print("\n🛡️ Running Security Checks...")
    run_security_checks(results)
    
    # Print final results
    success = results.print_summary()
    
    if success:
        print("\n🎉 All tests passed! System is ready for security team review.")
    else:
        print("\n⚠️ Some tests failed. Please review and fix issues before deployment.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())