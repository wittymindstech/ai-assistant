import asyncio
import time
import logging
from typing import Dict, Any
from datetime import datetime
import psutil
import os

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitor system resources and GenAI performance."""

    def __init__(self):
        self.start_time = time.time()
        self.cpu_samples = []
        self.memory_samples = []

    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system resource metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Keep rolling averages
        self.cpu_samples.append(cpu_percent)
        self.memory_samples.append(memory.percent)

        if len(self.cpu_samples) > 60:  # Keep last 60 samples (1 minute)
            self.cpu_samples.pop(0)
            self.memory_samples.pop(0)

        return {
            "cpu_percent": cpu_percent,
            "cpu_average_1min": sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0,
            "memory_percent": memory.percent,
            "memory_used_mb": memory.used / 1024 / 1024,
            "memory_available_mb": memory.available / 1024 / 1024,
            "disk_used_percent": disk.percent,
            "disk_free_gb": disk.free / 1024 / 1024 / 1024,
            "uptime_seconds": time.time() - self.start_time,
        }

    def collect_process_metrics(self) -> Dict[str, Any]:
        """Collect process-specific metrics."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_times = process.cpu_times()

            return {
                "process_memory_mb": memory_info.rss / 1024 / 1024,
                "process_cpu_percent": process.cpu_percent(),
                "process_threads": process.num_threads(),
                "process_open_files": len(process.open_files()),
                "process_connections": len(process.connections()),
            }
        except Exception as e:
            logger.error(f"Failed to collect process metrics: {e}")
            return {}

class GenAIMonitor:
    """Comprehensive GenAI monitoring and alerting."""

    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.alerts = []
        self.thresholds = {
            "max_response_time_ms": 30000,  # 30 seconds
            "max_error_rate_percent": 10.0,
            "max_cpu_percent": 90.0,
            "max_memory_percent": 90.0,
            "min_remaining_tokens": 1000,
        }

    def check_alerts(self, metrics_summary: Dict[str, Any], system_metrics: Dict[str, Any]) -> list:
        """Check for alert conditions."""
        alerts = []

        # AI-specific alerts
        ai_metrics = metrics_summary.get("ai_metrics", {})

        if ai_metrics.get("average_response_time_ms", 0) > self.thresholds["max_response_time_ms"]:
            alerts.append({
                "level": "warning",
                "message": f"High AI response time: {ai_metrics['average_response_time_ms']:.1f}ms",
                "metric": "response_time",
                "value": ai_metrics["average_response_time_ms"],
                "threshold": self.thresholds["max_response_time_ms"]
            })

        if ai_metrics.get("error_rate", 0) > self.thresholds["max_error_rate_percent"]:
            alerts.append({
                "level": "error",
                "message": f"High AI error rate: {ai_metrics['error_rate']:.1f}%",
                "metric": "error_rate",
                "value": ai_metrics["error_rate"],
                "threshold": self.thresholds["max_error_rate_percent"]
            })

        # System alerts
        if system_metrics.get("cpu_percent", 0) > self.thresholds["max_cpu_percent"]:
            alerts.append({
                "level": "warning",
                "message": f"High CPU usage: {system_metrics['cpu_percent']:.1f}%",
                "metric": "cpu_usage",
                "value": system_metrics["cpu_percent"],
                "threshold": self.thresholds["max_cpu_percent"]
            })

        if system_metrics.get("memory_percent", 0) > self.thresholds["max_memory_percent"]:
            alerts.append({
                "level": "error",
                "message": f"High memory usage: {system_metrics['memory_percent']:.1f}%",
                "metric": "memory_usage",
                "value": system_metrics["memory_percent"],
                "threshold": self.thresholds["max_memory_percent"]
            })

        return alerts

    def get_monitoring_report(self, metrics_collector, health_checker) -> Dict[str, Any]:
        """Generate comprehensive monitoring report."""
        metrics_summary = metrics_collector.get_metrics_summary()
        system_metrics = self.system_monitor.collect_system_metrics()
        process_metrics = self.system_monitor.collect_process_metrics()
        health_status = health_checker.get_health_status()

        alerts = self.check_alerts(metrics_summary, system_metrics)

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "metrics": {
                "genai": metrics_summary,
                "system": system_metrics,
                "process": process_metrics,
                "health": health_status,
            },
            "alerts": alerts,
            "summary": {
                "total_ai_requests": metrics_summary["ai_metrics"]["total_requests"],
                "active_alerts": len(alerts),
                "system_load": "high" if system_metrics["cpu_percent"] > 70 else "normal",
                "ai_health": health_status["overall"],
            }
        }

        # Determine overall status
        if alerts:
            critical_alerts = [a for a in alerts if a["level"] == "error"]
            report["status"] = "critical" if critical_alerts else "warning"

        return report

# Global monitor instance
genai_monitor = GenAIMonitor()