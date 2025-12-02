"""
Application-wide constants.
Centralized location for all constants used across the application.
"""

# Shift codes and their configurations
SHIFT_COLORS = {
    "A": "#0d6efd",  # Blue
    "B": "#198754",  # Green
    "C": "#ffc107",  # Yellow/Amber
    "G": "#6f42c1",  # Purple
}

SHIFT_TIMES = {
    "A": {"start": "09:00", "end": "17:00"},
    "B": {"start": "17:00", "end": "01:00"},
    "C": {"start": "21:00", "end": "05:00"},
    "G": {"start": "06:00", "end": "14:00"},
}

VALID_SHIFT_CODES = ["A", "B", "C", "G"]

# User roles
ROLES = {
    "MANAGER": "manager",
    "MEMBER": "member",
}

VALID_ROLES = list(ROLES.values())

# File upload settings
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB

# Notification types
NOTIFICATION_TYPES = {
    "SHIFT_CHANGE_REQUEST": "shift_change_request",
    "SHIFT_SWAP_REQUEST": "swap_request",
    "SHIFT_APPROVED": "shift_approved",
    "SHIFT_REJECTED": "shift_rejected",
    "SHIFT_ASSIGNED": "shift_assigned",
}

# Request statuses
REQUEST_STATUS = {
    "PENDING": "pending",
    "APPROVED": "approved",
    "REJECTED": "rejected",
}

# Date formats
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Cache keys (if implementing caching)
CACHE_KEYS = {
    "USER_PROJECTS": "user_projects_{user_id}",
    "PROJECT_MEMBERS": "project_members_{project_id}",
    "USER_SHIFTS": "user_shifts_{user_id}",
}

# API response messages
API_MESSAGES = {
    "SUCCESS": "Operation completed successfully",
    "ERROR": "An error occurred",
    "NOT_FOUND": "Resource not found",
    "UNAUTHORIZED": "Unauthorized access",
    "FORBIDDEN": "Access forbidden",
    "VALIDATION_ERROR": "Validation failed",
}

