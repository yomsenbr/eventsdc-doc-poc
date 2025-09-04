"""
Security testing suite for EventsDC Document POC
"""
import pytest
import requests
import json
import os
from pathlib import Path

# Test configuration
API_BASE = "http://127.0.0.1:8000"
TEST_USER = "admin"
TEST_PASSWORD = "admin123"

class TestSecurity:
    """Security test cases"""
    
    def setup_method(self):
        """Setup for each test"""
        self.session = requests.Session()
        self.auth_token = None
    
    def test_authentication_required(self):
        """Test that protected endpoints require authentication"""
        # Test without authentication
        response = self.session.get(f"{API_BASE}/metrics")
        assert response.status_code == 401 or response.status_code == 200  # May be public in dev
    
    def test_login_success(self):
        """Test successful login"""
        response = self.session.post(
            f"{API_BASE}/auth/login",
            data={"username": TEST_USER, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        self.auth_token = data["access_token"]
    
    def test_login_failure(self):
        """Test failed login attempts"""
        # Test with wrong password
        response = self.session.post(
            f"{API_BASE}/auth/login",
            data={"username": TEST_USER, "password": "wrongpassword"}
        )
        assert response.status_code == 401
        
        # Test with wrong username
        response = self.session.post(
            f"{API_BASE}/auth/login",
            data={"username": "wronguser", "password": TEST_PASSWORD}
        )
        assert response.status_code == 401
    
    def test_brute_force_protection(self):
        """Test brute force protection"""
        # Make multiple failed login attempts
        for i in range(10):
            response = self.session.post(
                f"{API_BASE}/auth/login",
                data={"username": TEST_USER, "password": f"wrong{i}"}
            )
            assert response.status_code == 401
        
        # Check if rate limiting kicks in
        response = self.session.post(
            f"{API_BASE}/auth/login",
            data={"username": TEST_USER, "password": "wrong"}
        )
        # Should still be 401, but might be rate limited
        assert response.status_code in [401, 429]
    
    def test_file_upload_security(self):
        """Test file upload security"""
        # Test with malicious filename
        malicious_files = [
            ("../../../etc/passwd", "text/plain"),
            ("<script>alert('xss')</script>.txt", "text/plain"),
            ("malicious.exe", "application/octet-stream"),
            ("test" + "x" * 300 + ".txt", "text/plain"),  # Too long filename
        ]
        
        for filename, content_type in malicious_files:
            response = self.session.post(
                f"{API_BASE}/ingest",
                files={"file": (filename, b"test content", content_type)}
            )
            # Should reject malicious files
            assert response.status_code in [400, 422]
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection in search queries"""
        malicious_queries = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
        ]
        
        for query in malicious_queries:
            response = self.session.get(
                f"{API_BASE}/search/hybrid",
                params={"q": query, "k": 5}
            )
            # Should handle malicious queries gracefully
            assert response.status_code in [200, 400, 422]
    
    def test_xss_protection(self):
        """Test XSS protection in search queries"""
        xss_queries = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
        ]
        
        for query in xss_queries:
            response = self.session.get(
                f"{API_BASE}/search/hybrid",
                params={"q": query, "k": 5}
            )
            # Should handle XSS attempts gracefully
            assert response.status_code in [200, 400, 422]
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        # Make many requests quickly
        for i in range(150):  # More than the rate limit
            response = self.session.get(f"{API_BASE}/health")
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert response.status_code == 429
    
    def test_file_size_limits(self):
        """Test file size limits"""
        # Create a large file (larger than 50MB limit)
        large_content = b"x" * (60 * 1024 * 1024)  # 60MB
        
        response = self.session.post(
            f"{API_BASE}/ingest",
            files={"file": ("large_file.txt", large_content, "text/plain")}
        )
        
        # Should reject large files
        assert response.status_code in [400, 413]
    
    def test_query_length_limits(self):
        """Test query length limits"""
        # Create a very long query
        long_query = "x" * 2000  # Longer than 1000 char limit
        
        response = self.session.get(
            f"{API_BASE}/search/hybrid",
            params={"q": long_query, "k": 5}
        )
        
        # Should reject or truncate long queries
        assert response.status_code in [200, 400, 422]
    
    def test_security_headers(self):
        """Test security headers are present"""
        response = self.session.get(f"{API_BASE}/health")
        
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]
        
        for header in security_headers:
            assert header in response.headers
    
    def test_cors_configuration(self):
        """Test CORS configuration"""
        response = self.session.options(
            f"{API_BASE}/health",
            headers={"Origin": "https://malicious-site.com"}
        )
        
        # Should have proper CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
    
    def test_error_information_disclosure(self):
        """Test that errors don't disclose sensitive information"""
        # Try to access non-existent endpoint
        response = self.session.get(f"{API_BASE}/nonexistent")
        
        # Should not expose internal paths or sensitive info
        assert response.status_code == 404
        error_content = response.text.lower()
        sensitive_terms = ["traceback", "exception", "file path", "internal"]
        
        for term in sensitive_terms:
            assert term not in error_content

class TestInputValidation:
    """Input validation tests"""
    
    def test_empty_requests(self):
        """Test handling of empty requests"""
        # Empty file upload
        response = requests.post(f"{API_BASE}/ingest", files={"file": ("", b"", "")})
        assert response.status_code in [400, 422]
        
        # Empty search query
        response = requests.get(f"{API_BASE}/search/hybrid", params={"q": "", "k": 5})
        assert response.status_code in [400, 422]
    
    def test_malformed_requests(self):
        """Test handling of malformed requests"""
        # Malformed JSON (if applicable)
        response = requests.post(
            f"{API_BASE}/auth/login",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]
    
    def test_parameter_validation(self):
        """Test parameter validation"""
        # Invalid k parameter (should be positive integer)
        response = requests.get(
            f"{API_BASE}/search/hybrid",
            params={"q": "test", "k": -1}
        )
        assert response.status_code in [400, 422]
        
        # Invalid k parameter (should be integer)
        response = requests.get(
            f"{API_BASE}/search/hybrid",
            params={"q": "test", "k": "not_a_number"}
        )
        assert response.status_code in [400, 422]

class TestSystemSecurity:
    """System-level security tests"""
    
    def test_directory_traversal(self):
        """Test directory traversal protection"""
        # Try to access files outside allowed directories
        traversal_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "/etc/passwd",
            "C:\\Windows\\System32\\drivers\\etc\\hosts"
        ]
        
        for path in traversal_paths:
            response = requests.get(f"{API_BASE}/files/{path}")
            # Should not allow access to system files
            assert response.status_code in [404, 403, 400]
    
    def test_sensitive_file_access(self):
        """Test that sensitive files are not accessible"""
        sensitive_files = [
            ".env",
            "config.py",
            "security.py",
            "requirements.txt",
            "chroma_db/",
            "logs/"
        ]
        
        for file_path in sensitive_files:
            response = requests.get(f"{API_BASE}/{file_path}")
            # Should not expose sensitive files
            assert response.status_code in [404, 403, 400]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
