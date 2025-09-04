#!/usr/bin/env python3
"""
Production deployment script for EventsDC Document POC
"""
import os
import sys
import subprocess
import shutil
import secrets
from pathlib import Path

def run_command(cmd, check=True):
    """Run a command and return the result"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result

def generate_secret_key():
    """Generate a secure secret key"""
    return secrets.token_urlsafe(32)

def setup_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "data/uploads",
        "data/processed",
        "chroma_db",
        "tests"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

def install_dependencies():
    """Install Python dependencies"""
    print("Installing dependencies...")
    run_command("pip install -r requirements.txt")

def setup_environment():
    """Setup production environment"""
    env_file = Path(".env")
    if not env_file.exists():
        print("Creating production environment file...")
        
        # Generate secure secret key
        secret_key = generate_secret_key()
        
        env_content = f"""# EventsDC Document POC - Production Environment
SECRET_KEY={secret_key}
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
WORKERS=4
MAX_FILE_SIZE=52428800
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
"""
        
        with open(env_file, "w") as f:
            f.write(env_content)
        
        print(f"Created .env file with secret key: {secret_key[:8]}...")
    else:
        print(".env file already exists")

def setup_logging():
    """Setup logging configuration"""
    print("Setting up logging...")
    
    # Create log rotation script
    logrotate_script = """#!/bin/bash
# Log rotation for EventsDC Document POC
find logs/ -name "*.log" -mtime +7 -delete
"""
    
    with open("scripts/rotate_logs.sh", "w") as f:
        f.write(logrotate_script)
    
    # Make executable
    os.chmod("scripts/rotate_logs.sh", 0o755)

def setup_systemd_service():
    """Create systemd service file"""
    service_content = f"""[Unit]
Description=EventsDC Document POC
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory={os.getcwd()}
Environment=PATH={os.getcwd()}/.venv/bin
ExecStart={os.getcwd()}/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    with open("eventsdc-doc-poc.service", "w") as f:
        f.write(service_content)
    
    print("Created systemd service file: eventsdc-doc-poc.service")
    print("To install: sudo cp eventsdc-doc-poc.service /etc/systemd/system/")
    print("To enable: sudo systemctl enable eventsdc-doc-poc")
    print("To start: sudo systemctl start eventsdc-doc-poc")

def setup_nginx_config():
    """Create nginx configuration"""
    nginx_config = """server {
    listen 80;
    server_name your-domain.com;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # File upload size limit
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files
    location /static/ {
        alias /path/to/your/static/files/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
"""
    
    with open("nginx/eventsdc-doc-poc.conf", "w") as f:
        f.write(nginx_config)
    
    print("Created nginx configuration: nginx/eventsdc-doc-poc.conf")

def run_security_tests():
    """Run security tests"""
    print("Running security tests...")
    try:
        result = run_command("python -m pytest tests/test_security.py -v", check=False)
        if result.returncode == 0:
            print("✅ Security tests passed")
        else:
            print("⚠️  Some security tests failed - review before production")
            print(result.stdout)
    except Exception as e:
        print(f"Could not run security tests: {e}")

def create_backup_script():
    """Create backup script"""
    backup_script = """#!/bin/bash
# Backup script for EventsDC Document POC
BACKUP_DIR="/backup/eventsdc-doc-poc"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
tar -czf $BACKUP_DIR/chroma_db_$DATE.tar.gz chroma_db/

# Backup uploaded files
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz data/uploads/

# Backup logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
"""
    
    with open("scripts/backup.sh", "w") as f:
        f.write(backup_script)
    
    os.chmod("scripts/backup.sh", 0o755)
    print("Created backup script: scripts/backup.sh")

def main():
    """Main deployment function"""
    print("🚀 EventsDC Document POC - Production Deployment")
    print("=" * 50)
    
    # Check if running as root (not recommended)
    if os.geteuid() == 0:
        print("⚠️  Warning: Running as root is not recommended for production")
    
    # Setup steps
    steps = [
        ("Setting up directories", setup_directories),
        ("Installing dependencies", install_dependencies),
        ("Setting up environment", setup_environment),
        ("Setting up logging", setup_logging),
        ("Creating systemd service", setup_systemd_service),
        ("Creating nginx config", setup_nginx_config),
        ("Creating backup script", create_backup_script),
        ("Running security tests", run_security_tests),
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        try:
            step_func()
            print(f"✅ {step_name} completed")
        except Exception as e:
            print(f"❌ {step_name} failed: {e}")
            sys.exit(1)
    
    print("\n🎉 Production deployment setup completed!")
    print("\n📋 Next steps:")
    print("1. Review and customize the configuration files")
    print("2. Set up SSL certificates for HTTPS")
    print("3. Configure firewall rules")
    print("4. Set up monitoring and alerting")
    print("5. Test the deployment in a staging environment")
    print("6. Deploy to production")
    
    print("\n🔒 Security checklist:")
    print("- Change default passwords")
    print("- Update SECRET_KEY in .env file")
    print("- Configure proper CORS origins")
    print("- Set up SSL/TLS certificates")
    print("- Configure firewall rules")
    print("- Set up log monitoring")
    print("- Regular security updates")

if __name__ == "__main__":
    main()
