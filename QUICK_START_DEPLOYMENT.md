# 🚀 Quick Start Deployment Guide

## **For Your Security Team & Other Teams**

This guide provides the fastest way to deploy the EventsDC Document POC to a production server for testing.

## 📋 **Prerequisites**

- **Server**: Ubuntu 20.04+ with public IP
- **Domain**: A domain name pointing to your server
- **Access**: SSH access to the server
- **Time**: 15-20 minutes for complete deployment

## ⚡ **One-Command Deployment**

### **Step 1: Connect to Your Server**
```bash
ssh your-username@your-server-ip
```

### **Step 2: Run the Automated Deployment Script**
```bash
# Download and run the deployment script
curl -fsSL https://raw.githubusercontent.com/your-username/eventsdc-doc-poc/main/deploy.sh -o deploy.sh
chmod +x deploy.sh
./deploy.sh
```

**The script will ask for:**
- Your domain name (e.g., `yourdomain.com`)
- Your email address (for SSL certificate)

### **Step 3: Wait for Completion**
The script will automatically:
- ✅ Install Docker and Docker Compose
- ✅ Set up SSL certificates with Let's Encrypt
- ✅ Configure NGINX with security headers
- ✅ Deploy the application with Docker
- ✅ Set up monitoring and logging

## 🎯 **Access Your Deployed System**

Once deployment is complete, you'll have:

### **🌐 Main URLs**
- **Application**: `https://yourdomain.com`
- **API Docs**: `https://yourdomain.com/docs`
- **Health Check**: `https://yourdomain.com/health`

### **🔐 Default Login**
- **Username**: `admin`
- **Password**: `admin123`
- **⚠️ Change these immediately!**

## 🧪 **Quick Testing**

### **Test 1: Health Check**
```bash
curl https://yourdomain.com/health
```

### **Test 2: Upload a Document**
```bash
curl -X POST https://yourdomain.com/ingest \
  -F "file=@your-document.pdf"
```

### **Test 3: Search Documents**
```bash
curl "https://yourdomain.com/search/hybrid?q=your%20search%20query&k=5"
```

### **Test 4: Chat Interface**
```bash
curl "https://yourdomain.com/chat?q=what%20is%20this%20document%20about?&k=5"
```

## 🔒 **Security Testing**

### **Authentication Testing**
```bash
# Test login
curl -X POST https://yourdomain.com/auth/login \
  -d "username=admin&password=admin123"

# Test invalid login
curl -X POST https://yourdomain.com/auth/login \
  -d "username=admin&password=wrong"
```

### **File Upload Security**
```bash
# Test malicious filename
curl -X POST https://yourdomain.com/ingest \
  -F "file=@test.txt;filename=../../../etc/passwd"

# Test oversized file
curl -X POST https://yourdomain.com/ingest \
  -F "file=@large_file.txt"  # > 50MB
```

### **Input Validation**
```bash
# Test SQL injection
curl "https://yourdomain.com/search/hybrid?q='; DROP TABLE users; --"

# Test XSS
curl "https://yourdomain.com/search/hybrid?q=<script>alert('xss')</script>"
```

## 📊 **Monitoring**

### **Check System Status**
```bash
# View container status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check system health
curl https://yourdomain.com/health | jq .
```

### **View Metrics**
```bash
# System metrics (restricted access)
curl https://yourdomain.com/metrics

# Security events (restricted access)
curl https://yourdomain.com/security/events
```

## 🛠️ **Management Commands**

### **Start/Stop Services**
```bash
# Start services
docker-compose -f docker-compose.prod.yml up -d

# Stop services
docker-compose -f docker-compose.prod.yml down

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

### **Update Application**
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### **Backup Data**
```bash
# Create backup
tar -czf backup_$(date +%Y%m%d).tar.gz data/ chroma_db/ logs/

# Restore backup
tar -xzf backup_20240101.tar.gz
```

## 🔧 **Configuration**

### **Change Default Credentials**
1. Edit `.env.production` file
2. Update `SECRET_KEY` and other security settings
3. Restart services: `docker-compose -f docker-compose.prod.yml restart`

### **Update CORS Settings**
1. Edit `.env.production` file
2. Update `CORS_ORIGINS` with your domains
3. Restart services: `docker-compose -f docker-compose.prod.yml restart`

## 🚨 **Troubleshooting**

### **Common Issues**

**1. SSL Certificate Issues**
```bash
# Renew certificate
sudo certbot renew

# Check certificate status
sudo certbot certificates
```

**2. Application Not Starting**
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs app

# Check container status
docker-compose -f docker-compose.prod.yml ps
```

**3. Permission Issues**
```bash
# Fix permissions
sudo chown -R $USER:$USER /opt/eventsdc-doc-poc
```

**4. Port Already in Use**
```bash
# Check what's using port 80/443
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443

# Stop conflicting services
sudo systemctl stop nginx
sudo systemctl stop apache2
```

## 📞 **Support**

### **Getting Help**
- Check logs: `docker-compose -f docker-compose.prod.yml logs`
- View system status: `./monitor.sh`
- Check health: `curl https://yourdomain.com/health`

### **Useful Commands**
```bash
# View all containers
docker ps -a

# View system resources
docker stats

# View disk usage
df -h

# View memory usage
free -h
```

## ✅ **Deployment Checklist**

- [ ] Server has public IP and domain name
- [ ] Domain points to server IP
- [ ] SSH access to server
- [ ] Deployment script completed successfully
- [ ] SSL certificate working
- [ ] Application accessible via HTTPS
- [ ] Default credentials changed
- [ ] Security testing completed
- [ ] Monitoring set up
- [ ] Backup procedures in place

---

**🎉 Your EventsDC Document POC is now live and ready for testing!**

**Access URL**: `https://yourdomain.com`
**API Documentation**: `https://yourdomain.com/docs`
**Default Login**: admin / admin123 (change immediately!)

**Happy Testing!** 🚀
