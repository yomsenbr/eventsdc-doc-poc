"""
Security module for EventsDC Document POC
Implements authentication, authorization, and security best practices
"""
import os
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import logging

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
security = HTTPBearer()

# Rate limiting (simple in-memory store for demo)
rate_limit_store = {}
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour

# File upload security
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "50")) * 1024 * 1024  # 50MB
ALLOWED_FILE_TYPES = {".pdf", ".docx", ".pptx", ".txt"}
DANGEROUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".scr", ".pif", ".com", ".vbs", ".js"}

# Input validation
MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "1000"))
MAX_FILENAME_LENGTH = int(os.getenv("MAX_FILENAME_LENGTH", "255"))

class SecurityManager:
    """Centralized security management"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """Check if client has exceeded rate limit"""
        current_time = datetime.utcnow().timestamp()
        window_start = current_time - RATE_LIMIT_WINDOW
        
        # Clean old entries
        rate_limit_store[client_ip] = [
            req_time for req_time in rate_limit_store.get(client_ip, [])
            if req_time > window_start
        ]
        
        # Check current requests
        current_requests = len(rate_limit_store.get(client_ip, []))
        if current_requests >= RATE_LIMIT_REQUESTS:
            return False
        
        # Add current request
        rate_limit_store[client_ip] = rate_limit_store.get(client_ip, []) + [current_time]
        return True
    
    def validate_file_upload(self, filename: str, file_size: int, content_type: str) -> Dict[str, Any]:
        """Validate file upload for security"""
        errors = []
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            errors.append(f"File size {file_size} exceeds maximum {MAX_FILE_SIZE}")
        
        # Check filename length
        if len(filename) > MAX_FILENAME_LENGTH:
            errors.append(f"Filename too long (max {MAX_FILENAME_LENGTH} characters)")
        
        # Check file extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in DANGEROUS_EXTENSIONS:
            errors.append(f"Dangerous file type: {file_ext}")
        elif file_ext not in ALLOWED_FILE_TYPES:
            errors.append(f"Unsupported file type: {file_ext}")
        
        # Check for path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            errors.append("Invalid filename: path traversal detected")
        
        # Check for suspicious patterns
        suspicious_patterns = ["<script", "javascript:", "data:", "vbscript:"]
        if any(pattern in filename.lower() for pattern in suspicious_patterns):
            errors.append("Suspicious filename pattern detected")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "sanitized_filename": self.sanitize_filename(filename)
        }
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove path separators and dangerous characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
        sanitized = "".join(c for c in filename if c in safe_chars)
        
        # Ensure it's not empty and has reasonable length
        if not sanitized or len(sanitized) < 3:
            sanitized = f"file_{secrets.token_hex(8)}"
        
        return sanitized[:MAX_FILENAME_LENGTH]
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate search query for security"""
        errors = []
        
        # Check length
        if len(query) > MAX_QUERY_LENGTH:
            errors.append(f"Query too long (max {MAX_QUERY_LENGTH} characters)")
        
        # Check for SQL injection patterns
        sql_patterns = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_", "exec", "execute"]
        if any(pattern in query.lower() for pattern in sql_patterns):
            errors.append("Potentially malicious query pattern detected")
        
        # Check for script injection
        script_patterns = ["<script", "javascript:", "onload=", "onerror=", "onclick="]
        if any(pattern in query.lower() for pattern in script_patterns):
            errors.append("Script injection pattern detected")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "sanitized_query": query.strip()[:MAX_QUERY_LENGTH]
        }
    
    def log_security_event(self, event_type: str, details: Dict[str, Any], client_ip: str = None):
        """Log security events for monitoring"""
        self.logger.warning(f"SECURITY_EVENT: {event_type} - {details} - IP: {client_ip}")

# Global security manager instance
security_manager = SecurityManager()

# Dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = security_manager.verify_token(token)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    return payload

async def check_rate_limit(client_ip: str = None) -> bool:
    """Check rate limit for client"""
    if not client_ip:
        return True  # Skip rate limiting if no IP available
    
    if not security_manager.check_rate_limit(client_ip):
        security_manager.log_security_event("RATE_LIMIT_EXCEEDED", {"ip": client_ip}, client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    return True

def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require admin privileges"""
    if not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user

# Security headers middleware
def get_security_headers() -> Dict[str, str]:
    """Get security headers for responses"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }
