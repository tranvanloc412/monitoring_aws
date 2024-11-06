"""
AWS Manager Package

A collection of utilities for managing AWS resources, including:
- Landing Zone configuration
- IAM session management
- CloudWatch metrics and alarms
- Resource scanning and management
"""

__version__ = "0.1.0"

from .landing_zone.manager import LandingZone, LandingZoneManager
from .iam import AWSSession, SessionManager
from .cloudwatch import MetricConfig, ThresholdConfig, AlarmManager
from .resources import ResourceScanner

__all__ = [
    # Landing Zone related
    "LandingZone",
    "LandingZoneManager",
    
    # IAM related
    "AWSSession",
    "SessionManager",
    
    # CloudWatch related
    "MetricConfig",
    "ThresholdConfig",
    "AlarmManager",
    
    # Resource related
    "ResourceScanner",
]
