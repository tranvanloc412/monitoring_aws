"""
AWS Manager Package

A collection of utilities for managing AWS resources, including:
- Landing Zone configuration
- IAM session management
- CloudWatch metrics and alarms
- Resource scanning and management
"""

__version__ = "0.1.0"

from .core import LandingZone, LandingZoneManager, AWSSession, SessionManager, ResourceScanner
from .monitoring import AlarmManager, AlarmConfig, MonitoringConfig, MetricSettings

__all__ = [
    # Landing Zone related
    "LandingZone",
    "LandingZoneManager",
    
    # IAM related
    "AWSSession",
    "SessionManager",
    
    # Monitoring related
    "AlarmManager",
    "AlarmConfig",
    "MonitoringConfig",
    "MetricSettings",
    
    # Resource related
    "ResourceScanner",
]
