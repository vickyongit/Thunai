import logging
from pymongo import MongoClient

logger = logging.getLogger(__name__)


class DatabaseUnavailable(Exception):
    """Raised when MongoDB is not configured or not reachable."""


class Mongo:
    def __init__(self):
        self.cx = None
        self.db = None

    def init_app(self, app):
        uri = app.config.get("MONGO_URI")
        db_name = app.config.get("DB_NAME") or "thunai"
        try:
            self.cx = MongoClient(uri, serverSelectionTimeoutMS=3000)
            self.db = self.cx[db_name]
            logger.info("MongoDB client created for database '%s'", db_name)
        except Exception as e:
            logger.error("Could not create MongoDB client: %s", e)
            self.cx = None
            self.db = None

    def get_db(self):
        if self.db is None:
            raise DatabaseUnavailable("Database unavailable")
        return self.db

    def is_connected(self):
        try:
            if self.cx is None:
                return False
            self.cx.admin.command("ping")
            return True
        except Exception:
            return False


mongo = Mongo()