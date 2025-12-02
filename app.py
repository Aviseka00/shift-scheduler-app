from flask import Flask, redirect, url_for, session, render_template, request
from dotenv import load_dotenv
from config import Config
from extensions import mongo

# Core components
from core.logger import setup_logging
from core.module_registry import registry

# Existing modules
from auth.routes import auth_bp
from manager import manager_bp
from member import member_bp
from project.routes import project_bp

# Load environment variables from .env file
load_dotenv()


def create_app(config_class=Config):
    """
    Application factory pattern for creating Flask app instances.
    This allows for easy testing and configuration management.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Setup logging
    setup_logging(app)

    # Ensure upload folder exists
    import os
    upload_folder = app.config.get("UPLOAD_FOLDER", "static/uploads/profile_pics")
    os.makedirs(upload_folder, exist_ok=True)

    # Initialize extensions
    mongo.init_app(app)

    # Register existing blueprints (backward compatibility)
    app.register_blueprint(auth_bp)
    app.register_blueprint(manager_bp, url_prefix="/manager")
    app.register_blueprint(member_bp, url_prefix="/member")
    app.register_blueprint(project_bp, url_prefix="/project")

    # Register all modules from registry (for future modules)
    registry.register_all_blueprints(app)
    registry.initialize_all_modules(app)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        if request.is_json:
            from flask import jsonify
            return jsonify({"error": "Not found"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error("Internal error: " + str(error))
        if request.is_json:
            from flask import jsonify
            return jsonify({"error": "Internal server error"}), 500
        return render_template("errors/500.html"), 500

    @app.route("/")
    def index():
        if "user_id" in session:
            if session.get("role") == "manager":
                return redirect("/manager/dashboard")
            else:
                return redirect("/member/dashboard")
        return render_template("index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        debug=app.config.get("DEBUG", False),
        host="127.0.0.1",
        port=5001   # ← FORCE PORT HERE
    )
