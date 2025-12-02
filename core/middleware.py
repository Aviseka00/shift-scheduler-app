"""
Middleware for request processing.
"""

from functools import wraps
from flask import request, jsonify, session
from typing import Callable, Optional
from core.exceptions import UnauthorizedError, ForbiddenError
import logging

logger = logging.getLogger(__name__)


class Middleware:
    """
    Base middleware class.
    """
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    def process_request(self, request):
        """
        Process the request before it reaches the route.
        Return None to continue, or a response to short-circuit.
        """
        return None
    
    def process_response(self, request, response):
        """
        Process the response before it's sent to the client.
        """
        return response


class AuthMiddleware(Middleware):
    """
    Authentication middleware.
    """
    
    def process_request(self, request):
        # Add user info to request if authenticated
        if "user_id" in session:
            request.user_id = session.get("user_id")
            request.user_role = session.get("role")
        return None


class LoggingMiddleware(Middleware):
    """
    Request logging middleware.
    """
    
    def process_request(self, request):
        logger.info(f"{request.method} {request.path} - User: {session.get('user_id', 'Anonymous')}")
        return None
    
    def process_response(self, request, response):
        logger.info(f"Response: {response.status_code} for {request.path}")
        return response


def require_role(role: str):
    """
    Decorator to require a specific role.
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                if request.is_json:
                    return jsonify({"error": "Unauthorized"}), 401
                from flask import redirect
                return redirect("/login")
            
            if session.get("role") != role:
                if request.is_json:
                    return jsonify({"error": "Forbidden"}), 403
                from flask import redirect, flash
                flash("Access denied.", "danger")
                return redirect("/login")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_roles(*roles: str):
    """
    Decorator to require one of multiple roles.
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                if request.is_json:
                    return jsonify({"error": "Unauthorized"}), 401
                from flask import redirect
                return redirect("/login")
            
            if session.get("role") not in roles:
                if request.is_json:
                    return jsonify({"error": "Forbidden"}), 403
                from flask import redirect, flash
                flash("Access denied.", "danger")
                return redirect("/login")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

