"""
Core application components.
This module provides base classes and utilities for building scalable features.
"""

from .base import BaseModule, BaseService, BaseValidator
from .exceptions import AppException, ValidationError, NotFoundError, UnauthorizedError

__all__ = [
    "BaseModule",
    "BaseService",
    "BaseValidator",
    "AppException",
    "ValidationError",
    "NotFoundError",
    "UnauthorizedError",
]

