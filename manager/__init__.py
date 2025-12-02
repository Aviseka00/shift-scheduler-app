from flask import Blueprint

# Correct blueprint configuration
from flask import Blueprint

manager_bp = Blueprint(
    "manager",
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

from . import routes
