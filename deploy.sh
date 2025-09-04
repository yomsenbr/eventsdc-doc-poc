#!/bin/bash
# EventsDC Document POC - Automated Deployment Script

set -e

echo "🚀 EventsDC Document POC - Automated Deployment"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root"
    exit 1
fi

# Get domain name from user
read -p "Enter your domain name (e.g., yourdomain.com): " DOMAIN
if [ -z "$DOMAIN" ]; then
    print_error "Domain name is required"
    exit 1
fi

# Get email for Let's Encrypt
read -p "Enter your email for SSL certificate: " EMAIL
if [ -z "$EMAIL" ]; then
    print_error "Email is required for SSL certificate"
    exit 1
fi

print_status "Starting deployment for domain: $DOMAIN"

# Step 1: Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Step 2: Install Docker
print_status "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    print_status "Docker installed successfully"
else
    print_status "Docker already installed"
fi

# Step 3: Install Docker Compose
print_status "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_status "Docker Compose installed successfully"
else
    print_status "Docker Compose already installed"
fi

# Step 4: Install additional tools
print_status "Installing additional tools..."
sudo apt install -y git nginx certbot python3-certbot-nginx curl jq

# Step 5: Create deployment directory
print_status "Setting up deployment directory..."
sudo mkdir -p /opt/eventsdc-doc-poc
sudo chown $USER:$USER /opt/eventsdc-doc-poc
cd /opt/eventsdc-doc-poc

# Step 6: Clone repository (if not already present)
if [ ! -d ".git" ]; then
    print_status "Cloning repository..."
    git clone https://github.com/your-username/eventsdc-doc-poc.git .
else
    print_status "Repository already exists, updating..."
    git pull
fi

# Step 7: Create production environment
print_status "Creating production environment..."
cat > .env.production << EOF
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

# Security Settings
SECRET_KEY=$(openssl rand -base64 32)
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

# CORS Configuration
CORS_ORIGINS=["https://$DOMAIN", "https://www.$DOMAIN"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET", "POST", "PUT", "DELETE"]
CORS_ALLOW_HEADERS=["*"]

# External Services
TESSERACT_PATH=/usr/bin/tesseract
POPPLER_PATH=/usr/bin
EOF

# Step 8: Create Docker Compose configuration
print_status "Creating Docker Compose configuration..."
cat > docker-compose.prod.yml << EOF
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

# Step 9: Create production Dockerfile
print_status "Creating production Dockerfile..."
cat > Dockerfile.prod << EOF
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    tesseract-ocr \\
    poppler-utils \\
    curl \\
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
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
EOF

# Step 10: Create NGINX configuration
print_status "Creating NGINX configuration..."
mkdir -p nginx/conf.d logs/nginx ssl

# Main nginx configuration
cat > nginx/nginx.conf << EOF
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
    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" "\$http_x_forwarded_for"';

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
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone \$binary_remote_addr zone=login:10m rate=5r/m;

    # Include site configurations
    include /etc/nginx/conf.d/*.conf;
}
EOF

# Site configuration
cat > nginx/conf.d/eventsdc-doc-poc.conf << EOF
upstream app {
    server app:8000;
}

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

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
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header X-Forwarded-Host \$host;
    proxy_set_header X-Forwarded-Port \$server_port;

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

# Step 11: Create SSL certificate
print_status "Creating SSL certificate..."
sudo certbot certonly --standalone -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --non-interactive

# Copy certificates to ssl directory
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*.pem

# Step 12: Configure firewall
print_status "Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Step 13: Build and start services
print_status "Building and starting services..."
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Step 14: Wait for services to start
print_status "Waiting for services to start..."
sleep 30

# Step 15: Verify deployment
print_status "Verifying deployment..."
if curl -s -k https://$DOMAIN/health > /dev/null; then
    print_status "Deployment successful!"
    echo
    echo "🌐 Access URLs:"
    echo "   Main Application: https://$DOMAIN"
    echo "   API Documentation: https://$DOMAIN/docs"
    echo "   Health Check: https://$DOMAIN/health"
    echo
    echo "🔐 Default Credentials:"
    echo "   Username: admin"
    echo "   Password: admin123"
    echo "   ⚠️  IMPORTANT: Change these credentials immediately!"
    echo
    echo "📊 System Status:"
    docker-compose -f docker-compose.prod.yml ps
    echo
    print_warning "Please change the default credentials and review the security configuration!"
else
    print_error "Deployment failed. Check logs with: docker-compose -f docker-compose.prod.yml logs"
    exit 1
fi

# Step 16: Create monitoring script
print_status "Creating monitoring script..."
cat > monitor.sh << 'EOF'
#!/bin/bash
echo "=== EventsDC Document POC Status ==="
echo "Date: $(date)"
echo
echo "Container Status:"
docker-compose -f docker-compose.prod.yml ps
echo
echo "Application Health:"
curl -s -k https://your-domain.com/health | jq .
EOF

chmod +x monitor.sh

print_status "Deployment completed successfully!"
print_warning "Remember to:"
print_warning "1. Change default credentials"
print_warning "2. Review security configuration"
print_warning "3. Monitor system logs"
print_warning "4. Set up regular backups"
