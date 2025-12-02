"""
Base classes for building scalable modules.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from flask import current_app
from extensions import mongo


class BaseModule(ABC):
    """
    Base class for application modules.
    All modules should inherit from this class to ensure consistency.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.config = {}
    
    @abstractmethod
    def register_routes(self, blueprint):
        """
        Register routes for this module.
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def get_permissions(self) -> Dict[str, List[str]]:
        """
        Return permissions required by this module.
        Format: {role: [permission1, permission2, ...]}
        """
        pass
    
    def initialize(self, app):
        """
        Initialize the module with the Flask app.
        Override this method for custom initialization.
        """
        pass
    
    def cleanup(self):
        """
        Cleanup resources when module is unloaded.
        Override this method for custom cleanup.
        """
        pass


class BaseService(ABC):
    """
    Base class for service layer.
    Services contain business logic separated from routes.
    """
    
    def __init__(self):
        self.db = mongo.db if mongo else None
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate input data.
        Must be implemented by subclasses.
        """
        pass
    
    def get_by_id(self, collection: str, id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID from a collection."""
        if not self.db:
            return None
        try:
            from bson.objectid import ObjectId
            return self.db[collection].find_one({"_id": ObjectId(id)})
        except Exception:
            return None
    
    def create(self, collection: str, data: Dict[str, Any]) -> Optional[str]:
        """Create a new document in a collection."""
        if not self.db:
            return None
        try:
            result = self.db[collection].insert_one(data)
            return str(result.inserted_id)
        except Exception:
            return None
    
    def update(self, collection: str, id: str, data: Dict[str, Any]) -> bool:
        """Update a document in a collection."""
        if not self.db:
            return False
        try:
            from bson.objectid import ObjectId
            result = self.db[collection].update_one(
                {"_id": ObjectId(id)},
                {"$set": data}
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    def delete(self, collection: str, id: str) -> bool:
        """Delete a document from a collection."""
        if not self.db:
            return False
        try:
            from bson.objectid import ObjectId
            result = self.db[collection].delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except Exception:
            return False


class BaseValidator(ABC):
    """
    Base class for validators.
    Validators handle input validation and sanitization.
    """
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate data.
        Returns: (is_valid, error_message)
        """
        pass
    
    def sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize input data.
        Override this method for custom sanitization.
        """
        return data

