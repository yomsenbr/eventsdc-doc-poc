# EventsDC Document POC - Production Security System

## 🔒 **PRODUCTION-READY SECURITY SYSTEM**

This is a **hardened, production-ready version** of the EventsDC Document POC designed specifically for security testing and evaluation by your security team.

## 🛡️ **Security Features Implemented**

### **Authentication & Authorization**
- ✅ JWT-based authentication with access/refresh tokens
- ✅ Password hashing using bcrypt
- ✅ Rate limiting on authentication endpoints
- ✅ Brute force protection with IP tracking
- ✅ Session management and token expiration

### **Input Validation & Security**
- ✅ File upload validation (type, size, content)
- ✅ SQL injection prevention
- ✅ XSS protection
- ✅ Path traversal prevention
- ✅ Input length limits and sanitization
- ✅ Content-Type validation

### **Security Headers & Middleware**
- ✅ Comprehensive security headers
- ✅ CORS configuration
- ✅ Trusted host middleware
- ✅ Request logging and monitoring
- ✅ Error handling without information disclosure

### **File Upload Security**
- ✅ File type validation (PDF, DOCX, PPTX, TXT only)
- ✅ File size limits (50MB maximum)
- ✅ Filename sanitization
- ✅ Dangerous extension blocking
- ✅ Path traversal protection

### **Monitoring & Logging**
- ✅ Security event logging
- ✅ System metrics collection
- ✅ Health check endpoints
- ✅ Performance monitoring
- ✅ Failed login tracking

## 🚀 **Quick Start for Security Testing**

### **1. Install Dependencies**
```bash
# Install production dependencies
pip install -r requirements.txt
```

### **2. Configure Environment**
```bash
# Copy production environment template
cp env.production .env

# Edit .env file with your settings
# IMPORTANT: Change SECRET_KEY and other sensitive values
```

### **3. Start the System**
```bash
# Start in production mode
python start_production.py
```

### **4. Access the System**
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Security Events**: http://localhost:8000/security/events

## 🧪 **Security Testing**

### **Run Automated Security Tests**
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run comprehensive security test suite
python -m pytest tests/test_security.py -v
```

### **Manual Security Testing**

#### **Authentication Testing**
```bash
# Test login
curl -X POST "http://localhost:8000/auth/login" \
  -d "username=admin&password=admin123"

# Test brute force protection
for i in {1..10}; do
  curl -X POST "http://localhost:8000/auth/login" \
    -d "username=admin&password=wrong$i"
done
```

#### **File Upload Security Testing**
```bash
# Test malicious filename
curl -X POST "http://localhost:8000/ingest" \
  -F "file=@test.txt;filename=../../../etc/passwd"

# Test oversized file
curl -X POST "http://localhost:8000/ingest" \
  -F "file=@large_file.txt"  # > 50MB

# Test dangerous file type
curl -X POST "http://localhost:8000/ingest" \
  -F "file=@malicious.exe"
```

#### **Input Validation Testing**
```bash
# Test SQL injection
curl "http://localhost:8000/search/hybrid?q='; DROP TABLE users; --"

# Test XSS
curl "http://localhost:8000/search/hybrid?q=<script>alert('xss')</script>"

# Test rate limiting
for i in {1..150}; do
  curl "http://localhost:8000/health"
done
```

## 📊 **Security Monitoring**

### **Key Endpoints for Security Testing**

| Endpoint | Purpose | Security Focus |
|----------|---------|----------------|
| `/auth/login` | Authentication | Brute force, credential testing |
| `/ingest` | File upload | Malicious files, size limits |
| `/search/*` | Search queries | Injection attacks, XSS |
| `/metrics` | System metrics | Performance, resource usage |
| `/security/events` | Security logs | Attack detection, monitoring |
| `/health` | Health check | System status, availability |

### **Security Event Types to Monitor**

- `LOGIN_FAILED` - Failed authentication attempts
- `RATE_LIMIT_EXCEEDED` - Rate limit violations
- `INVALID_FILE_UPLOAD` - Malicious file upload attempts
- `HTTP_ERROR` - 4xx/5xx errors
- `BRUTE_FORCE_ATTEMPT` - Multiple failed logins from same IP

## 🔧 **Configuration for Security Testing**

### **Environment Variables**
```bash
# Security Settings
SECRET_KEY=your-super-secret-key-minimum-32-characters
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# File Upload Security
MAX_FILE_SIZE=52428800  # 50MB
MAX_FILENAME_LENGTH=255
MAX_QUERY_LENGTH=1000

# CORS (configure for your testing environment)
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8501"]
```

## 🎯 **Security Testing Scenarios**

### **1. Authentication Security**
- Test credential brute forcing
- Test token manipulation
- Test session hijacking
- Test password policy enforcement

### **2. File Upload Security**
- Test malicious file uploads
- Test file size limits
- Test file type validation
- Test path traversal attacks

### **3. Input Validation**
- Test SQL injection attacks
- Test XSS attacks
- Test command injection
- Test parameter manipulation

### **4. Rate Limiting & DoS**
- Test rate limit enforcement
- Test resource exhaustion
- Test memory exhaustion
- Test CPU exhaustion

### **5. Information Disclosure**
- Test error message leakage
- Test directory traversal
- Test sensitive file access
- Test debug information exposure

## 📋 **Security Testing Checklist**

### **Pre-Testing Setup**
- [ ] System is running in production mode
- [ ] All security features are enabled
- [ ] Logging is configured and working
- [ ] Monitoring endpoints are accessible
- [ ] Default credentials are changed

### **Authentication Testing**
- [ ] Test valid login credentials
- [ ] Test invalid login credentials
- [ ] Test brute force protection
- [ ] Test token expiration
- [ ] Test refresh token functionality

### **File Upload Testing**
- [ ] Test valid file uploads
- [ ] Test malicious file uploads
- [ ] Test oversized file uploads
- [ ] Test file type validation
- [ ] Test filename sanitization

### **Input Validation Testing**
- [ ] Test SQL injection attempts
- [ ] Test XSS attempts
- [ ] Test command injection
- [ ] Test parameter manipulation
- [ ] Test long input handling

### **System Security Testing**
- [ ] Test rate limiting
- [ ] Test error handling
- [ ] Test information disclosure
- [ ] Test directory traversal
- [ ] Test system resource limits

## 🚨 **Security Incident Response**

### **If Security Issues Are Found**
1. **Document the issue** with detailed steps to reproduce
2. **Check security logs** for related events
3. **Assess the impact** and potential exploitation
4. **Report immediately** to the development team
5. **Monitor for similar attacks** in the future

### **Security Logs Location**
- Application logs: `logs/app.log`
- Security events: Available via `/security/events` endpoint
- System metrics: Available via `/metrics` endpoint

## 📞 **Support & Contact**

For security concerns or questions:
- Review the `SECURITY.md` file for detailed security documentation
- Check the security test results
- Contact the development team for clarification

## ⚠️ **Important Security Notes**

1. **This is a production-ready system** with comprehensive security measures
2. **All security features are enabled** by default
3. **Default credentials are provided** for testing (admin/admin123)
4. **Change default credentials** before any real-world deployment
5. **Monitor security logs** during testing for attack patterns
6. **This system is designed** to withstand common security attacks

---

**🔒 Ready for Security Testing!**

This system has been specifically hardened and prepared for comprehensive security testing by your security team. All common attack vectors have been addressed with appropriate countermeasures.
