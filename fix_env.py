#!/usr/bin/env python3
"""
Helper script to create a properly formatted .env file
"""
from urllib.parse import quote_plus

print("=" * 60)
print("MongoDB Atlas Connection String Helper")
print("=" * 60)
print()

# Get connection details
username = input("Enter MongoDB username: ").strip()
password = input("Enter MongoDB password: ").strip()
cluster = input("Enter cluster address (e.g., cluster0.syq2mmr.mongodb.net): ").strip()
database = input("Enter database name (default: shift_scheduler_db): ").strip() or "shift_scheduler_db"

# URL encode credentials
encoded_username = quote_plus(username)
encoded_password = quote_plus(password)

# Build the connection string
mongo_uri = f"mongodb+srv://{encoded_username}:{encoded_password}@{cluster}/{database}?retryWrites=true&w=majority"

# Get secret key
secret_key = input("Enter a secret key (or press Enter for default): ").strip() or "change-this-secret-key-in-production"

# Create .env content
env_content = f'''# MongoDB Atlas Connection String
MONGO_URI="{mongo_uri}"

# Flask Secret Key
SECRET_KEY="{secret_key}"
'''

# Write to .env file
try:
    with open(".env", "w") as f:
        f.write(env_content)
    print()
    print("✓ Successfully created .env file!")
    print()
    print("Your .env file contains:")
    print("-" * 60)
    print(env_content)
    print("-" * 60)
    print()
    print("You can now run: python app.py")
except Exception as e:
    print(f"✗ Error creating .env file: {e}")

