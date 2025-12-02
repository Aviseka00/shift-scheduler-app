"""
Service for shift-related business logic.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from services.base_service import BaseService
from core.exceptions import ValidationError, NotFoundError
from constants import SHIFT_COLORS, SHIFT_TIMES, VALID_SHIFT_CODES
import logging

logger = logging.getLogger(__name__)


class ShiftService(BaseService):
    """
    Service for managing shifts.
    """
    
    def __init__(self):
        super().__init__("shifts")
    
    def validate_shift_data(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate shift data."""
        required_fields = ["user_id", "date", "shift_code"]
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if data["shift_code"] not in VALID_SHIFT_CODES:
            return False, f"Invalid shift code: {data['shift_code']}"
        
        # Validate date format
        try:
            datetime.strptime(data["date"], "%Y-%m-%d")
        except ValueError:
            return False, "Invalid date format. Use YYYY-MM-DD"
        
        return True, None
    
    def create_shift(self, data: Dict[str, Any]) -> Optional[str]:
        """Create a new shift."""
        is_valid, error = self.validate_shift_data(data)
        if not is_valid:
            raise ValidationError(error)
        
        # Set default times if not provided
        shift_code = data["shift_code"]
        if "start_time" not in data:
            data["start_time"] = SHIFT_TIMES.get(shift_code, {}).get("start", "09:00")
        if "end_time" not in data:
            data["end_time"] = SHIFT_TIMES.get(shift_code, {}).get("end", "17:00")
        
        # Add timestamps
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        
        return self.create(data)
    
    def get_user_shifts(self, user_id: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get shifts for a user."""
        query = {"user_id": ObjectId(user_id)}
        
        if start_date:
            query["date"] = {"$gte": start_date}
        if end_date:
            if "date" in query and isinstance(query["date"], dict):
                query["date"]["$lte"] = end_date
            else:
                query["date"] = {"$lte": end_date}
        
        return self.find_many(query, sort=[("date", 1)])
    
    def get_shifts_by_project(self, project_id: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get shifts for a project."""
        query = {"project_id": ObjectId(project_id)}
        
        if start_date:
            query["date"] = {"$gte": start_date}
        if end_date:
            if "date" in query and isinstance(query["date"], dict):
                query["date"]["$lte"] = end_date
            else:
                query["date"] = {"$lte": end_date}
        
        return self.find_many(query, sort=[("date", 1)])
    
    def check_conflict(self, user_id: str, date: str, shift_id: str = None) -> bool:
        """Check if a shift conflicts with existing shifts."""
        query = {
            "user_id": ObjectId(user_id),
            "date": date
        }
        
        if shift_id:
            query["_id"] = {"$ne": ObjectId(shift_id)}
        
        existing = self.find_one(query)
        return existing is not None
    
    def get_upcoming_shifts(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get upcoming shifts for a user."""
        today = datetime.now().strftime("%Y-%m-%d")
        query = {
            "user_id": ObjectId(user_id),
            "date": {"$gte": today}
        }
        return self.find_many(query, sort=[("date", 1)], limit=limit)
    
    def get_all_members_planned_shifts(self, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        Get all planned shifts for all members.
        Returns shifts with user information included.
        """
        query = {}
        
        if start_date:
            query["date"] = {"$gte": start_date}
        if end_date:
            if "date" in query and isinstance(query["date"], dict):
                query["date"]["$lte"] = end_date
            else:
                query["date"] = {"$lte": end_date}
        
        shifts = self.find_many(query, sort=[("date", 1), ("shift_code", 1)])
        
        # Get user information for each shift
        from services.user_service import UserService
        user_service = UserService()
        
        result = []
        for shift in shifts:
            user_id = str(shift.get("user_id"))
            user = user_service.find_by_id(user_id)
            
            shift_data = {
                "_id": str(shift.get("_id")),
                "date": shift.get("date"),
                "shift_code": shift.get("shift_code"),
                "start_time": shift.get("start_time", "09:00"),
                "end_time": shift.get("end_time", "17:00"),
                "task": shift.get("task", ""),
                "project_id": str(shift.get("project_id")) if shift.get("project_id") else None,
                "user_id": user_id,
                "user_name": user.get("name", "Unknown") if user else "Unknown",
                "user_email": user.get("email", "") if user else "",
            }
            result.append(shift_data)
        
        return result

