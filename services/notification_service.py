"""
Service for notification-related business logic.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from bson.objectid import ObjectId
from services.base_service import BaseService
from core.exceptions import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)


class NotificationService(BaseService):
    """
    Service for managing notifications.
    """
    
    def __init__(self):
        super().__init__("notifications")
    
    def create_notification(self, user_id: str, message: str, notification_type: str = None, related_id: str = None) -> Optional[str]:
        """Create a new notification."""
        data = {
            "user_id": ObjectId(user_id),
            "message": message,
            "read": False,
            "created_at": datetime.utcnow()
        }
        
        if notification_type:
            data["type"] = notification_type
        if related_id:
            data["related_id"] = ObjectId(related_id)
        
        return self.create(data)
    
    def get_user_notifications(self, user_id: str, unread_only: bool = False, limit: int = None) -> List[Dict[str, Any]]:
        """Get notifications for a user."""
        query = {"user_id": ObjectId(user_id)}
        if unread_only:
            query["read"] = False
        
        return self.find_many(query, sort=[("created_at", -1)], limit=limit)
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        return self.update(notification_id, {"read": True, "read_at": datetime.utcnow()})
    
    def mark_all_as_read(self, user_id: str) -> bool:
        """Mark all notifications as read for a user."""
        try:
            result = self.db[self.collection_name].update_many(
                {"user_id": ObjectId(user_id), "read": False},
                {"$set": {"read": True, "read_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error marking notifications as read: {str(e)}")
            return False

