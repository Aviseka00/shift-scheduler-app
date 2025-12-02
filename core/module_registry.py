"""
Module registry for dynamic module loading and registration.
This allows new features to be added without modifying core application code.
"""

from typing import Dict, List, Optional
from flask import Blueprint
from core.base import BaseModule
import logging

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """
    Central registry for all application modules.
    """
    
    _instance = None
    _modules: Dict[str, BaseModule] = {}
    _blueprints: Dict[str, Blueprint] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModuleRegistry, cls).__new__(cls)
        return cls._instance
    
    def register_module(self, module: BaseModule, blueprint: Blueprint, url_prefix: str = None):
        """
        Register a new module with the application.
        
        Args:
            module: Instance of BaseModule
            blueprint: Flask Blueprint for the module
            url_prefix: URL prefix for the blueprint (optional)
        """
        if module.name in self._modules:
            logger.warning(f"Module {module.name} is already registered. Overwriting.")
        
        self._modules[module.name] = module
        self._blueprints[module.name] = {
            "blueprint": blueprint,
            "url_prefix": url_prefix
        }
        logger.info(f"Module {module.name} registered successfully")
    
    def get_module(self, name: str) -> Optional[BaseModule]:
        """Get a registered module by name."""
        return self._modules.get(name)
    
    def get_all_modules(self) -> Dict[str, BaseModule]:
        """Get all registered modules."""
        return self._modules.copy()
    
    def get_blueprint(self, name: str) -> Optional[Dict]:
        """Get blueprint configuration for a module."""
        return self._blueprints.get(name)
    
    def register_all_blueprints(self, app):
        """
        Register all module blueprints with the Flask app.
        """
        for name, config in self._blueprints.items():
            blueprint = config["blueprint"]
            url_prefix = config.get("url_prefix")
            
            if url_prefix:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
            else:
                app.register_blueprint(blueprint)
            
            logger.info(f"Registered blueprint for module: {name}")
    
    def initialize_all_modules(self, app):
        """
        Initialize all registered modules.
        """
        for name, module in self._modules.items():
            try:
                module.initialize(app)
                logger.info(f"Initialized module: {name}")
            except Exception as e:
                logger.error(f"Failed to initialize module {name}: {str(e)}")
    
    def unregister_module(self, name: str):
        """
        Unregister a module.
        """
        if name in self._modules:
            module = self._modules[name]
            module.cleanup()
            del self._modules[name]
            del self._blueprints[name]
            logger.info(f"Unregistered module: {name}")


# Global registry instance
registry = ModuleRegistry()

