"""
Base service class with common database operations.
"""

from typing import Dict, List, Optional, Any
from bson.objectid import ObjectId
from extensions import mongo
from core.base import BaseService as CoreBaseService
from core.exceptions import NotFoundError, ValidationError
import logging

logger = logging.getLogger(__name__)


class BaseService(CoreBaseService):
    """
    Enhanced base service with common operations.
    """
    
    def __init__(self, collection_name: str):
        super().__init__()
        self.collection_name = collection_name
    
    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document."""
        try:
            return self.db[self.collection_name].find_one(query)
        except Exception as e:
            logger.error(f"Error finding document in {self.collection_name}: {str(e)}")
            return None
    
    def find_many(self, query: Dict[str, Any] = None, sort: List[tuple] = None, limit: int = None) -> List[Dict[str, Any]]:
        """Find multiple documents."""
        try:
            cursor = self.db[self.collection_name].find(query or {})
            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Error finding documents in {self.collection_name}: {str(e)}")
            return []
    
    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Find a document by ID."""
        try:
            return self.db[self.collection_name].find_one({"_id": ObjectId(id)})
        except Exception as e:
            logger.error(f"Error finding document by ID in {self.collection_name}: {str(e)}")
            return None
    
    def create(self, data: Dict[str, Any]) -> Optional[str]:
        """Create a new document."""
        try:
            result = self.db[self.collection_name].insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating document in {self.collection_name}: {str(e)}")
            return None
    
    def update(self, id: str, data: Dict[str, Any]) -> bool:
        """Update a document."""
        try:
            result = self.db[self.collection_name].update_one(
                {"_id": ObjectId(id)},
                {"$set": data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating document in {self.collection_name}: {str(e)}")
            return False
    
    def delete(self, id: str) -> bool:
        """Delete a document."""
        try:
            result = self.db[self.collection_name].delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting document in {self.collection_name}: {str(e)}")
            return False
    
    def count(self, query: Dict[str, Any] = None) -> int:
        """Count documents matching query."""
        try:
            return self.db[self.collection_name].count_documents(query or {})
        except Exception as e:
            logger.error(f"Error counting documents in {self.collection_name}: {str(e)}")
            return 0

