from flask import Blueprint

project_bp = Blueprint("project", __name__, template_folder="../templates/project")

from . import routes  # noqa
