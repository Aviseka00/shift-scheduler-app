from flask import Blueprint

member_bp = Blueprint("member", __name__, template_folder="../templates/member")

from . import routes  # noqa
