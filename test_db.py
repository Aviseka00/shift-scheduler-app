from pymongo import MongoClient

uri = "mongodb+srv://rorosapiroteam_db_user:Arjun%401234%2E@cluster0.syq2mmr.mongodb.net/shift_scheduler_db?retryWrites=true&w=majority"

client = MongoClient(uri)

try:
    client.admin.command("ping")
    print("Connected successfully!")
except Exception as e:
    print("Error:", e)
