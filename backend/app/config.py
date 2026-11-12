import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/thunai")
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
