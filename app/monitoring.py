"""
Monitoring and metrics for EventsDC Document POC
"""
import time
import logging
from typing import Dict, Any, Optional
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict, deque
import psutil
import os

class MetricsCollector:
    """Collect and store application metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics = {
            "requests": defaultdict(int),
            "response_times": deque(maxlen=1000),
            "errors": defaultdict(int),
            "file_uploads": defaultdict(int),
            "search_queries": defaultdict(int),
            "system": {}
        }
        self.start_time = time.time()
    
    def record_request(self, endpoint: str, method: str, status_code: int, response_time: float):
        """Record API request metrics"""
        key = f"{method} {endpoint}"
        self.metrics["requests"][key] += 1
        self.metrics["response_times"].append(response_time)
        
        if status_code >= 400:
            self.metrics["errors"][f"{status_code} {key}"] += 1
    
    def record_file_upload(self, filename: str, file_size: int, success: bool):
        """Record file upload metrics"""
        ext = os.path.splitext(filename)[1].lower()
        self.metrics["file_uploads"][f"{ext}_{'success' if success else 'failed'}"] += 1
    
    def record_search_query(self, query_type: str, query_length: int, results_count: int):
        """Record search query metrics"""
        self.metrics["search_queries"][f"{query_type}_queries"] += 1
        self.metrics["search_queries"][f"{query_type}_total_results"] += results_count
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            process = psutil.Process()
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "process_memory_mb": process.memory_info().rss / 1024 / 1024,
                "process_cpu_percent": process.cpu_percent(),
                "uptime_seconds": time.time() - self.start_time,
                "open_files": len(process.open_files()),
                "connections": len(process.connections()),
            }
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        response_times = list(self.metrics["response_times"])
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "requests": dict(self.metrics["requests"]),
            "errors": dict(self.metrics["errors"]),
            "file_uploads": dict(self.metrics["file_uploads"]),
            "search_queries": dict(self.metrics["search_queries"]),
            "response_times": {
                "average": avg_response_time,
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "count": len(response_times)
            },
            "system": self.get_system_metrics()
        }
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {
            "requests": defaultdict(int),
            "response_times": deque(maxlen=1000),
            "errors": defaultdict(int),
            "file_uploads": defaultdict(int),
            "search_queries": defaultdict(int),
            "system": {}
        }
        self.start_time = time.time()

# Global metrics collector
metrics_collector = MetricsCollector()

def monitor_request(endpoint: str, method: str = "GET"):
    """Decorator to monitor API requests"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                raise
            finally:
                response_time = time.time() - start_time
                metrics_collector.record_request(endpoint, method, status_code, response_time)
        
        return wrapper
    return decorator

class SecurityMonitor:
    """Monitor security events and anomalies"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.security_events = deque(maxlen=1000)
        self.failed_logins = defaultdict(list)
        self.suspicious_ips = set()
    
    def log_security_event(self, event_type: str, details: Dict[str, Any], client_ip: str = None):
        """Log security event"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "details": details,
            "client_ip": client_ip
        }
        
        self.security_events.append(event)
        self.logger.warning(f"SECURITY_EVENT: {event_type} - {details} - IP: {client_ip}")
        
        # Check for suspicious patterns
        self._check_suspicious_activity(event)
    
    def _check_suspicious_activity(self, event: Dict[str, Any]):
        """Check for suspicious activity patterns"""
        client_ip = event.get("client_ip")
        event_type = event.get("event_type")
        
        if not client_ip:
            return
        
        # Track failed logins
        if event_type == "LOGIN_FAILED":
            self.failed_logins[client_ip].append(datetime.utcnow())
            
            # Check for brute force attempts
            recent_failures = [
                failure for failure in self.failed_logins[client_ip]
                if datetime.utcnow() - failure < timedelta(minutes=15)
            ]
            
            if len(recent_failures) >= 5:
                self.suspicious_ips.add(client_ip)
                self.logger.critical(f"BRUTE_FORCE_ATTEMPT detected from IP: {client_ip}")
        
        # Check for rate limit violations
        if event_type == "RATE_LIMIT_EXCEEDED":
            self.suspicious_ips.add(client_ip)
            self.logger.warning(f"RATE_LIMIT_VIOLATION from IP: {client_ip}")
    
    def is_ip_suspicious(self, client_ip: str) -> bool:
        """Check if IP is flagged as suspicious"""
        return client_ip in self.suspicious_ips
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security events summary"""
        recent_events = [
            event for event in self.security_events
            if datetime.fromisoformat(event["timestamp"]) > datetime.utcnow() - timedelta(hours=24)
        ]
        
        return {
            "total_events_24h": len(recent_events),
            "suspicious_ips": list(self.suspicious_ips),
            "failed_logins_by_ip": {
                ip: len(failures) for ip, failures in self.failed_logins.items()
            },
            "recent_events": recent_events[-10:]  # Last 10 events
        }

# Global security monitor
security_monitor = SecurityMonitor()

class HealthChecker:
    """Check application health status"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and health"""
        try:
            # Simple health check without importing indexing module
            import os
            chroma_db_path = os.path.join("chroma_db", "chroma.sqlite3")
            if os.path.exists(chroma_db_path):
                return {
                    "status": "healthy",
                    "total_chunks": "available",
                    "error": None
                }
            else:
                return {
                    "status": "degraded",
                    "total_chunks": 0,
                    "error": "Database not initialized"
                }
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "total_chunks": 0,
                "error": str(e)
            }
    
    def check_file_system_health(self) -> Dict[str, Any]:
        """Check file system health"""
        try:
            upload_dir = "data/uploads"
            processed_dir = "data/processed"
            
            upload_exists = os.path.exists(upload_dir)
            processed_exists = os.path.exists(processed_dir)
            
            if upload_exists:
                upload_files = len(os.listdir(upload_dir))
            else:
                upload_files = 0
            
            return {
                "status": "healthy" if upload_exists and processed_exists else "degraded",
                "upload_dir_exists": upload_exists,
                "processed_dir_exists": processed_exists,
                "upload_files_count": upload_files,
                "error": None
            }
        except Exception as e:
            self.logger.error(f"File system health check failed: {e}")
            return {
                "status": "unhealthy",
                "upload_dir_exists": False,
                "processed_dir_exists": False,
                "upload_files_count": 0,
                "error": str(e)
            }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            system_metrics = metrics_collector.get_system_metrics()
            
            # Define thresholds
            cpu_threshold = 80
            memory_threshold = 85
            disk_threshold = 90
            
            cpu_ok = system_metrics.get("cpu_percent", 0) < cpu_threshold
            memory_ok = system_metrics.get("memory_percent", 0) < memory_threshold
            disk_ok = system_metrics.get("disk_percent", 0) < disk_threshold
            
            status = "healthy" if all([cpu_ok, memory_ok, disk_ok]) else "degraded"
            
            return {
                "status": status,
                "cpu_percent": system_metrics.get("cpu_percent", 0),
                "memory_percent": system_metrics.get("memory_percent", 0),
                "disk_percent": system_metrics.get("disk_percent", 0),
                "thresholds": {
                    "cpu": cpu_threshold,
                    "memory": memory_threshold,
                    "disk": disk_threshold
                },
                "error": None
            }
        except Exception as e:
            self.logger.error(f"System resources health check failed: {e}")
            return {
                "status": "unhealthy",
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_percent": 0,
                "thresholds": {},
                "error": str(e)
            }
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall application health"""
        database_health = self.check_database_health()
        filesystem_health = self.check_file_system_health()
        system_health = self.check_system_resources()
        
        # Determine overall status
        statuses = [
            database_health["status"],
            filesystem_health["status"],
            system_health["status"]
        ]
        
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": database_health,
                "filesystem": filesystem_health,
                "system": system_health
            }
        }

# Global health checker
health_checker = HealthChecker()
