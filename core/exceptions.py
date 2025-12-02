"""
Custom exceptions for the application.
"""


class AppException(Exception):
    """Base exception for all application exceptions."""
    
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Raised when validation fails."""
    
    def __init__(self, message: str, field: str = None, details: dict = None):
        super().__init__(message, status_code=400, details=details)
        self.field = field


class NotFoundError(AppException):
    """Raised when a resource is not found."""
    
    def __init__(self, resource: str, resource_id: str = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message, status_code=404)


class UnauthorizedError(AppException):
    """Raised when access is unauthorized."""
    
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(message, status_code=401)


class ForbiddenError(AppException):
    """Raised when access is forbidden."""
    
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, status_code=403)

