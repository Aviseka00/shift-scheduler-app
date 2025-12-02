"""
Service for user-related business logic.
"""

from typing import Dict, List, Optional, Any
from bson.objectid import ObjectId
from services.base_service import BaseService
from core.exceptions import ValidationError, NotFoundError
from constants import VALID_ROLES
import logging

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """
    Service for managing users.
    """
    
    def __init__(self):
        super().__init__("users")
    
    def validate_user_data(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate user data."""
        required_fields = ["name", "email", "role"]
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if data["role"] not in VALID_ROLES:
            return False, f"Invalid role: {data['role']}"
        
        # Validate email format (basic)
        if "@" not in data["email"]:
            return False, "Invalid email format"
        
        return True, None
    
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        return self.find_one({"email": email})
    
    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Get all users with a specific role."""
        return self.find_many({"role": role})
    
    def get_users_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all users assigned to a project."""
        try:
            return self.find_many({"project_ids": ObjectId(project_id)})
        except:
            return []
    
    def assign_project(self, user_id: str, project_id: str) -> bool:
        """Assign a project to a user."""
        try:
            user = self.find_by_id(user_id)
            if not user:
                raise NotFoundError("User", user_id)
            
            project_ids = user.get("project_ids", [])
            project_obj_id = ObjectId(project_id)
            
            if project_obj_id not in project_ids:
                project_ids.append(project_obj_id)
                return self.update(user_id, {"project_ids": project_ids})
            
            return True
        except Exception as e:
            logger.error(f"Error assigning project: {str(e)}")
            return False
    
    def remove_project(self, user_id: str, project_id: str) -> bool:
        """Remove a project from a user."""
        try:
            user = self.find_by_id(user_id)
            if not user:
                raise NotFoundError("User", user_id)
            
            project_ids = user.get("project_ids", [])
            project_obj_id = ObjectId(project_id)
            
            if project_obj_id in project_ids:
                project_ids.remove(project_obj_id)
                return self.update(user_id, {"project_ids": project_ids})
            
            return True
        except Exception as e:
            logger.error(f"Error removing project: {str(e)}")
            return False

