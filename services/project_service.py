"""
Service for project-related business logic.
"""

from typing import Dict, List, Optional, Any
from bson.objectid import ObjectId
from services.base_service import BaseService
from core.exceptions import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)


class ProjectService(BaseService):
    """
    Service for managing projects.
    """
    
    def __init__(self):
        super().__init__("projects")
    
    def validate_project_data(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate project data."""
        if "name" not in data or not data["name"]:
            return False, "Project name is required"
        
        return True, None
    
    def get_project_members(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all members assigned to a project."""
        from services.user_service import UserService
        user_service = UserService()
        return user_service.get_users_by_project(project_id)
    
    def get_project_shifts(self, project_id: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get all shifts for a project."""
        from services.shift_service import ShiftService
        shift_service = ShiftService()
        return shift_service.get_shifts_by_project(project_id, start_date, end_date)

