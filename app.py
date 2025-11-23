from flask import Flask, redirect, url_for, session, render_template
from dotenv import load_dotenv
from config import Config
from extensions import mongo

from auth.routes import auth_bp
from manager.routes import manager_bp
from member.routes import member_bp
from project.routes import project_bp

# Load environment variables from .env file
load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    mongo.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(manager_bp, url_prefix="/manager")
    app.register_blueprint(member_bp, url_prefix="/member")
    app.register_blueprint(project_bp, url_prefix="/project")

    @app.route("/")
    def index():
        if "user_id" in session:
            if session.get("role") == "manager":
                return redirect(url_for("manager.dashboard"))
            else:
                return redirect(url_for("member.dashboard"))
        return render_template("index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
