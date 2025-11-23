import os
from urllib.parse import quote_plus

def _fix_mongo_uri(uri):
    """Fix MongoDB URI by properly encoding username and password."""
    if not uri:
        return uri
    
    # Remove quotes if present
    uri = uri.strip().strip('"').strip("'")
    
    if not uri.startswith("mongodb"):
        return uri
    
    try:
        # Split the URI into parts
        if "mongodb+srv://" in uri:
            prefix = "mongodb+srv://"
            rest = uri[len(prefix):]
        elif "mongodb://" in uri:
            prefix = "mongodb://"
            rest = uri[len(prefix):]
        else:
            return uri
        
        # Find where credentials end (before @)
        if "@" in rest:
            credentials, host_part = rest.split("@", 1)
            if ":" in credentials:
                username, password = credentials.split(":", 1)
                # URL encode username and password (handle special chars like @, ., etc.)
                encoded_username = quote_plus(username)
                encoded_password = quote_plus(password)
                # Reconstruct URI
                return f"{prefix}{encoded_username}:{encoded_password}@{host_part}"
    except Exception as e:
        # If anything fails, return original (will show error but app won't crash)
        print(f"Warning: Could not encode MongoDB URI: {e}")
        return uri
    
    return uri

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "change-this-secret"
    _raw_mongo_uri = os.environ.get("MONGO_URI") or "mongodb://localhost:27017/shift_scheduler_db"
    MONGO_URI = _fix_mongo_uri(_raw_mongo_uri)

    # Email / SMTP
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or MAIL_USERNAME

