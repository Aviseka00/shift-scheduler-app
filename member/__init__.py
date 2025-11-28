from flask import Blueprint

member_bp = Blueprint("member", __name__, template_folder="../templates/member")

# Import routes to register them with the blueprint
from . import routes  # noqa
