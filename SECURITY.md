# Security Documentation - EventsDC Document POC

## 🔒 Security Overview

This document outlines the security measures implemented in the EventsDC Document POC system and provides guidance for security testing and hardening.

## 🛡️ Security Features Implemented

### Authentication & Authorization
- **JWT-based authentication** with access and refresh tokens
- **Password hashing** using bcrypt
- **Token expiration** and refresh mechanisms
- **Rate limiting** on authentication endpoints
- **Brute force protection** with IP tracking

### Input Validation & Sanitization
- **File upload validation** with type, size, and content checks
- **Query sanitization** to prevent injection attacks
- **Filename sanitization** to prevent path traversal
- **Input length limits** on all user inputs
- **Content-Type validation** for file uploads

### Security Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'`
- `Referrer-Policy: strict-origin-when-cross-origin`

### File Upload Security
- **File type validation** (only PDF, DOCX, PPTX, TXT allowed)
- **File size limits** (50MB maximum)
- **Filename sanitization** and length limits
- **Dangerous extension blocking** (.exe, .bat, .cmd, etc.)
- **Path traversal protection**

### Rate Limiting
- **Request rate limiting** (100 requests per hour per IP)
- **Per-endpoint rate limiting** for sensitive operations
- **IP-based tracking** with automatic blocking
- **Graceful degradation** when limits are exceeded

### Logging & Monitoring
- **Security event logging** for all suspicious activities
- **Failed login tracking** with IP monitoring
- **Request logging** with response times and status codes
- **System metrics collection** (CPU, memory, disk usage)
- **Health check endpoints** for monitoring

## 🧪 Security Testing

### Automated Security Tests

Run the comprehensive security test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run security tests
python -m pytest tests/test_security.py -v
```

### Manual Security Testing

#### 1. Authentication Testing
```bash
# Test successful login
curl -X POST "http://localhost:8000/auth/login" \
  -d "username=admin&password=admin123"

# Test failed login (should be rate limited after multiple attempts)
curl -X POST "http://localhost:8000/auth/login" \
  -d "username=admin&password=wrongpassword"
```

#### 2. File Upload Security Testing
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

#### 3. Input Validation Testing
```bash
# Test SQL injection
curl "http://localhost:8000/search/hybrid?q='; DROP TABLE users; --"

# Test XSS
curl "http://localhost:8000/search/hybrid?q=<script>alert('xss')</script>"

# Test long query
curl "http://localhost:8000/search/hybrid?q=$(python -c 'print("x"*2000)')"
```

#### 4. Rate Limiting Testing
```bash
# Test rate limiting
for i in {1..150}; do
  curl "http://localhost:8000/health"
done
```

## 🔧 Security Configuration

### Environment Variables

Critical security settings in your `.env` file:

```bash
# Authentication
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

# CORS (restrict in production)
CORS_ORIGINS=["https://yourdomain.com"]
```

### Production Security Checklist

- [ ] **Change default credentials** (admin/admin123)
- [ ] **Generate strong SECRET_KEY** (minimum 32 characters)
- [ ] **Configure proper CORS origins** (not wildcard)
- [ ] **Set up SSL/TLS certificates**
- [ ] **Configure firewall rules**
- [ ] **Set up log monitoring and alerting**
- [ ] **Regular security updates**
- [ ] **Backup and recovery procedures**
- [ ] **Access control and user management**
- [ ] **Network segmentation**

## 🚨 Security Monitoring

### Key Security Metrics to Monitor

1. **Failed Login Attempts**
   - Track by IP address
   - Alert on brute force attempts
   - Monitor for credential stuffing

2. **File Upload Anomalies**
   - Rejected file uploads
   - Suspicious file types
   - Oversized files

3. **Rate Limit Violations**
   - IPs hitting rate limits
   - Unusual traffic patterns
   - Potential DDoS attempts

4. **System Health**
   - CPU and memory usage
   - Disk space
   - Response times
   - Error rates

### Security Event Types

- `LOGIN_FAILED` - Failed authentication attempts
- `RATE_LIMIT_EXCEEDED` - Rate limit violations
- `INVALID_FILE_UPLOAD` - Malicious file upload attempts
- `HTTP_ERROR` - 4xx/5xx errors
- `BRUTE_FORCE_ATTEMPT` - Multiple failed logins from same IP

## 🔍 Vulnerability Assessment

### Common Vulnerabilities Addressed

1. **Injection Attacks**
   - SQL injection prevention through parameterized queries
   - NoSQL injection prevention through input validation
   - Command injection prevention through input sanitization

2. **Cross-Site Scripting (XSS)**
   - Input sanitization and validation
   - Content Security Policy headers
   - Output encoding

3. **Cross-Site Request Forgery (CSRF)**
   - CORS configuration
   - SameSite cookie attributes
   - Origin validation

4. **File Upload Vulnerabilities**
   - File type validation
   - Size limits
   - Content scanning
   - Path traversal prevention

5. **Authentication Bypass**
   - Strong password requirements
   - Rate limiting
   - Account lockout policies
   - Secure session management

## 🛠️ Security Hardening

### Additional Security Measures

1. **Network Security**
   - Use HTTPS in production
   - Implement WAF (Web Application Firewall)
   - Network segmentation
   - VPN access for admin functions

2. **Application Security**
   - Regular dependency updates
   - Code security scanning
   - Penetration testing
   - Security code review

3. **Infrastructure Security**
   - Secure server configuration
   - Regular security patches
   - Intrusion detection systems
   - Backup security

## 📞 Incident Response

### Security Incident Response Plan

1. **Detection**
   - Monitor security logs
   - Automated alerting
   - User reports

2. **Assessment**
   - Determine scope and impact
   - Identify attack vectors
   - Preserve evidence

3. **Containment**
   - Isolate affected systems
   - Block malicious IPs
   - Disable compromised accounts

4. **Recovery**
   - Patch vulnerabilities
   - Restore from backups
   - Monitor for recurrence

5. **Post-Incident**
   - Document lessons learned
   - Update security measures
   - Conduct security review

## 📋 Security Testing Checklist

### Pre-Production Testing

- [ ] Run automated security tests
- [ ] Manual penetration testing
- [ ] Code security review
- [ ] Dependency vulnerability scan
- [ ] Configuration security review
- [ ] Network security assessment

### Production Monitoring

- [ ] Security event monitoring
- [ ] Performance monitoring
- [ ] Log analysis
- [ ] Regular security scans
- [ ] Incident response testing

## 🔐 Compliance Considerations

### Data Protection
- Document metadata storage
- User data handling
- Log retention policies
- Data encryption at rest and in transit

### Audit Requirements
- Security event logging
- Access control logging
- Change management
- Regular security assessments

---

**⚠️ Important Security Notes:**

1. **This is a proof-of-concept system** - Additional security hardening is required for production use
2. **Default credentials must be changed** before any production deployment
3. **Regular security updates** are essential for maintaining security posture
4. **Professional security assessment** is recommended before production deployment
5. **Monitor security logs** continuously for suspicious activities

For security concerns or questions, contact the development team immediately.
