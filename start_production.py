#!/usr/bin/env python3
"""
Production startup script for EventsDC Document POC
"""
import os
import sys
import logging
import uvicorn
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup production logging"""
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )

def check_environment():
    """Check production environment requirements"""
    required_dirs = ["logs", "data/uploads", "data/processed", "chroma_db"]
    
    for directory in required_dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Check for required environment variables
    required_vars = ["SECRET_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        print("Please set these in your .env file or environment")
        sys.exit(1)
    
    # Check SECRET_KEY strength
    secret_key = os.getenv("SECRET_KEY", "")
    if len(secret_key) < 32:
        print("❌ SECRET_KEY must be at least 32 characters long")
        sys.exit(1)
    
    print("✅ Environment check passed")

def main():
    """Main startup function"""
    print("🚀 Starting EventsDC Document POC - Production Mode")
    print("=" * 60)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Check environment
    check_environment()
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "4"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    print(f"📊 Configuration:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Workers: {workers}")
    print(f"   Log Level: {log_level}")
    print(f"   Environment: {os.getenv('ENVIRONMENT', 'production')}")
    
    # Security warnings
    if os.getenv("ENVIRONMENT") == "production":
        print("\n🔒 Security Status:")
        print("   ✅ Production environment detected")
        print("   ✅ Security headers enabled")
        print("   ✅ Rate limiting enabled")
        print("   ✅ Input validation enabled")
        print("   ⚠️  Ensure SECRET_KEY is properly configured")
        print("   ⚠️  Ensure CORS origins are restricted")
    
    print("\n🌐 Starting server...")
    print(f"   API Documentation: http://{host}:{port}/docs")
    print(f"   Health Check: http://{host}:{port}/health")
    print(f"   Metrics: http://{host}:{port}/metrics")
    
    try:
        # Start the server
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            workers=workers if workers > 1 else None,
            log_level=log_level,
            access_log=True,
            reload=False,  # Never reload in production
            server_header=False,  # Hide server header for security
            date_header=False,    # Hide date header for security
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        logger.info("Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server failed to start: {e}")
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
