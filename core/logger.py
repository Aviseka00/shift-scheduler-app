"""
Logging configuration and utilities.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(app):
    """
    Configure logging for the application.
    """
    if not app.debug:
        # Production logging
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/shift_scheduler.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Shift Scheduler startup')
    else:
        # Development logging
        app.logger.setLevel(logging.DEBUG)


def get_logger(name: str = None):
    """
    Get a logger instance.
    """
    if name:
        return logging.getLogger(f"shift_scheduler.{name}")
    return logging.getLogger("shift_scheduler")

