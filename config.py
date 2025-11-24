import os

class Config:
    # Secret key for session management and cookies
    SECRET_KEY = os.environ.get("SECRET_KEY") or "change-this-secret"

    # MongoDB connection URI (Render reads this from Environment Variables)
    # DO NOT modify or encode the URI – use it EXACTLY as provided in Render
    MONGO_URI = os.environ.get("MONGO_URI") or "mongodb://localhost:27017/shift_scheduler_db"

    # Email / SMTP settings
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or MAIL_USERNAME


