import os


class Config:
    """
    Global configuration for the Flask app.
    """

    # Secret key
    SECRET_KEY = os.environ.get("SECRET_KEY") or "change-this-secret"

    # ------------------------------------------------------------------
    # MongoDB connection
    # ------------------------------------------------------------------
    MONGO_URI = os.environ.get("MONGO_URI") or "mongodb://localhost:27017/shift_scheduler_db"

    # ------------------------------------------------------------------
    # Email / SMTP settings (optional)
    # ------------------------------------------------------------------
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or MAIL_USERNAME

    # ------------------------------------------------------------------
    # FILE UPLOAD SETTINGS (VERY IMPORTANT)
    # ------------------------------------------------------------------
    UPLOAD_FOLDER = "static/uploads/profile_pics"
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024   # 4MB limit
