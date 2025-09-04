# EventsDC Document POC - Production Deployment Guide

## 🚀 **Complete Server Deployment Instructions**

This guide will help you deploy the EventsDC Document POC to a production server with Docker Compose, NGINX, and TLS for your security team and other teams to test.

## 📋 **Prerequisites**

### **Server Requirements**
- **OS**: Ubuntu 20.04+ or CentOS 8+ (recommended)
- **RAM**: Minimum 4GB, recommended 8GB+
- **CPU**: 2+ cores
- **Storage**: 50GB+ free space
- **Network**: Public IP with domain name (optional but recommended)

### **Software Requirements**
- Docker 20.10+
- Docker Compose 2.0+
- Git
- OpenSSL (for TLS certificates)

## 🔧 **Step 1: Server Setup**

### **1.1 Update System**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### **1.2 Install Docker**
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# CentOS/RHEL
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### **1.3 Install Docker Compose**
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### **1.4 Install Additional Tools**
```bash
# Ubuntu/Debian
sudo apt install -y git nginx certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install -y git nginx certbot python3-certbot-nginx
```

## 📦 **Step 2: Deploy the Application**

### **2.1 Clone Repository**
```bash
# Create deployment directory
sudo mkdir -p /opt/eventsdc-doc-poc
sudo chown $USER:$USER /opt/eventsdc-doc-poc
cd /opt/eventsdc-doc-poc

# Clone the repository
git clone https://github.com/your-username/eventsdc-doc-poc.git .
```

### **2.2 Create Production Environment**
```bash
# Create production environment file
cat > .env.production << 'EOF'
# EventsDC Document POC - Production Environment
APP_NAME=EventsDC Document POC
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4
RELOAD=false

# Security Settings (CHANGE THESE!)
SECRET_KEY=your-super-secret-production-key-minimum-32-characters-long
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# File Upload Security
MAX_FILE_SIZE=52428800
MAX_FILENAME_LENGTH=255
MAX_QUERY_LENGTH=1000

# Database Configuration
CHROMA_DB_DIR=/app/chroma_db
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Text Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
OCR_ENABLED=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090

# CORS Configuration (Update with your domains)
CORS_ORIGINS=["https://yourdomain.com", "https://app.yourdomain.com"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET", "POST", "PUT", "DELETE"]
CORS_ALLOW_HEADERS=["*"]

# External Services
TESSERACT_PATH=/usr/bin/tesseract
POPPLER_PATH=/usr/bin
EOF

# Generate a secure secret key
SECRET_KEY=$(openssl rand -base64 32)
sed -i "s/your-super-secret-production-key-minimum-32-characters-long/$SECRET_KEY/" .env.production

echo "✅ Production environment created with secure secret key"
```

### **2.3 Create Docker Compose Configuration**
```bash
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: eventsdc-doc-app
    restart: unless-stopped
    env_file:
      - .env.production
    volumes:
      - ./data:/app/data
      - ./chroma_db:/app/chroma_db
      - ./logs:/app/logs
    networks:
      - eventsdc-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    container_name: eventsdc-doc-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - app
    networks:
      - eventsdc-network

  redis:
    image: redis:alpine
    container_name: eventsdc-doc-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - eventsdc-network

volumes:
  redis_data:

networks:
  eventsdc-network:
    driver: bridge
EOF
```

### **2.4 Create Production Dockerfile**
```bash
cat > Dockerfile.prod << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data/uploads /app/data/processed /app/chroma_db /app/logs

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
EOF
```

### **2.5 Create NGINX Configuration**
```bash
# Create nginx directories
mkdir -p nginx/conf.d logs/nginx ssl

# Main nginx configuration
cat > nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 50M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    # Include site configurations
    include /etc/nginx/conf.d/*.conf;
}
EOF

# Site configuration
cat > nginx/conf.d/eventsdc-doc-poc.conf << 'EOF'
upstream app {
    server app:8000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # Rate limiting
    limit_req zone=api burst=20 nodelay;
    limit_req zone=login burst=5 nodelay;

    # Proxy settings
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;

    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # Main application
    location / {
        proxy_pass http://app;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://app/health;
        access_log off;
    }

    # Metrics endpoint (restrict access)
    location /metrics {
        proxy_pass http://app/metrics;
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
    }

    # Security events endpoint (restrict access)
    location /security/events {
        proxy_pass http://app/security/events;
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
    }
}
EOF
```

## 🔐 **Step 3: SSL/TLS Setup**

### **3.1 Option A: Let's Encrypt (Recommended)**
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal
sudo crontab -e
# Add this line:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### **3.2 Option B: Self-Signed Certificate (For Testing)**
```bash
# Create self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"

# Set permissions
sudo chmod 600 ssl/key.pem
sudo chmod 644 ssl/cert.pem
```

## 🚀 **Step 4: Deploy and Start**

### **4.1 Build and Start Services**
```bash
# Build the application
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
```

### **4.2 Verify Deployment**
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Test health endpoint
curl -k https://your-domain.com/health

# Test API documentation
curl -k https://your-domain.com/docs
```

## 🔧 **Step 5: Configuration Updates**

### **5.1 Update Domain Names**
```bash
# Update nginx configuration with your actual domain
sed -i 's/your-domain.com/your-actual-domain.com/g' nginx/conf.d/eventsdc-doc-poc.conf

# Update CORS origins in environment file
sed -i 's/yourdomain.com/your-actual-domain.com/g' .env.production

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

### **5.2 Configure Firewall**
```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## 📊 **Step 6: Monitoring and Maintenance**

### **6.1 Create Monitoring Script**
```bash
cat > monitor.sh << 'EOF'
#!/bin/bash
# Monitoring script for EventsDC Document POC

echo "=== EventsDC Document POC Status ==="
echo "Date: $(date)"
echo

# Check container status
echo "Container Status:"
docker-compose -f docker-compose.prod.yml ps
echo

# Check disk usage
echo "Disk Usage:"
df -h
echo

# Check memory usage
echo "Memory Usage:"
free -h
echo

# Check application health
echo "Application Health:"
curl -s -k https://your-domain.com/health | jq .
echo

# Check recent logs
echo "Recent Errors:"
docker-compose -f docker-compose.prod.yml logs --tail=50 | grep -i error
EOF

chmod +x monitor.sh
```

### **6.2 Create Backup Script**
```bash
cat > backup.sh << 'EOF'
#!/bin/bash
# Backup script for EventsDC Document POC

BACKUP_DIR="/opt/backups/eventsdc-doc-poc"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup data
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/

# Backup database
tar -czf $BACKUP_DIR/chroma_db_$DATE.tar.gz chroma_db/

# Backup logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x backup.sh
```

## 🧪 **Step 7: Testing the Deployment**

### **7.1 Test All Endpoints**
```bash
# Health check
curl -k https://your-domain.com/health

# API documentation
curl -k https://your-domain.com/docs

# Test file upload
curl -k -X POST https://your-domain.com/ingest \
  -F "file=@test.txt"

# Test search
curl -k "https://your-domain.com/search/hybrid?q=test&k=5"

# Test chat
curl -k "https://your-domain.com/chat?q=what%20is%20this%20about?&k=5"
```

### **7.2 Security Testing**
```bash
# Test authentication
curl -k -X POST https://your-domain.com/auth/login \
  -d "username=admin&password=admin123"

# Test rate limiting
for i in {1..20}; do
  curl -k https://your-domain.com/health
done

# Test SSL
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

## 📋 **Step 8: Access Information for Teams**

### **8.1 Create Access Guide**
```bash
cat > TEAM_ACCESS_GUIDE.md << 'EOF'
# EventsDC Document POC - Team Access Guide

## 🌐 **Access URLs**
- **Main Application**: https://your-domain.com
- **API Documentation**: https://your-domain.com/docs
- **Health Check**: https://your-domain.com/health

## 🔐 **Default Credentials**
- **Username**: admin
- **Password**: admin123
- **⚠️ IMPORTANT**: Change these credentials immediately!

## 📊 **Available Endpoints**

### **Public Endpoints**
- `GET /` - Application status
- `GET /health` - Health check
- `POST /auth/login` - User authentication
- `POST /ingest` - File upload
- `GET /search/keyword` - Keyword search
- `GET /search/vector` - Vector search
- `GET /search/hybrid` - Hybrid search (recommended)
- `GET /chat` - Natural language Q&A

### **Admin Endpoints** (Requires Authentication)
- `GET /metrics` - System metrics
- `GET /security/events` - Security events
- `POST /admin/reset` - Reset database
- `POST /admin/clear-logs` - Clear logs

## 🧪 **Testing Instructions**

### **1. File Upload Test**
```bash
curl -X POST https://your-domain.com/ingest \
  -F "file=@your-document.pdf"
```

### **2. Search Test**
```bash
curl "https://your-domain.com/search/hybrid?q=your%20search%20query&k=5"
```

### **3. Chat Test**
```bash
curl "https://your-domain.com/chat?q=what%20is%20this%20document%20about?&k=5"
```

## 🔒 **Security Testing**

### **Authentication Testing**
- Test login with valid credentials
- Test login with invalid credentials
- Test brute force protection
- Test token expiration

### **File Upload Security**
- Test malicious file uploads
- Test oversized files
- Test file type validation

### **Input Validation**
- Test SQL injection attempts
- Test XSS attempts
- Test rate limiting

## 📞 **Support**
For issues or questions, contact the development team.
EOF
```

## 🎯 **Step 9: Final Verification**

### **9.1 Complete System Check**
```bash
# Run the monitoring script
./monitor.sh

# Test all functionality
curl -k https://your-domain.com/health
curl -k https://your-domain.com/stats
curl -k "https://your-domain.com/search/hybrid?q=test&k=3"
```

### **9.2 Performance Test**
```bash
# Install Apache Bench for load testing
sudo apt install apache2-utils

# Run load test
ab -n 100 -c 10 https://your-domain.com/health
```

## ✅ **Deployment Complete!**

Your EventsDC Document POC is now deployed and ready for testing by your security team and other teams.

### **Next Steps:**
1. **Share access information** with your teams
2. **Change default credentials** immediately
3. **Monitor system performance** and logs
4. **Conduct security testing** as planned
5. **Gather feedback** from testing teams

### **Maintenance:**
- **Daily**: Check logs and system health
- **Weekly**: Run backups and security updates
- **Monthly**: Review performance metrics and security events

---

**🔒 Security Note**: This is a production-ready system with comprehensive security measures. All teams can now test the system safely and provide feedback for improvements.
