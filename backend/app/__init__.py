import logging
from flask import Flask, jsonify
from flask_cors import CORS
from pymongo.errors import (
    ConnectionFailure,
    DuplicateKeyError,
    ServerSelectionTimeoutError,
)
from werkzeug.exceptions import HTTPException

from .config import Config
from .extensions import DatabaseUnavailable, mongo

logger = logging.getLogger(__name__)


def _error(code, message, status):
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    # /api/contacts and /api/contacts/ both work (no 308 redirect that breaks CORS)
    app.url_map.strict_slashes = False

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # CORS: only allow the frontend (Vite dev server by default)
    client_url = app.config.get("CLIENT_URL", "http://localhost:5173")
    allowed_origins = list({client_url, "http://localhost:5173", "http://127.0.0.1:5173"})
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    mongo.init_app(app)

    # ---------- Blueprints ----------
    from .blueprints.health.routes import health_bp
    from .blueprints.auth.routes import auth_bp
    from .blueprints.profile.routes import profile_bp
    from .blueprints.contacts.routes import contacts_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(contacts_bp)

    # ---------- DB indexes (non-fatal if Mongo is down at startup) ----------
    with app.app_context():
        try:
            from .models.user import create_indexes
            from .models.contact import create_contact_indexes
            create_indexes()
            create_contact_indexes()
        except Exception as e:
            logger.warning("Could not create DB indexes at startup: %s", e)

    # ---------- Error handlers ----------
    @app.errorhandler(DatabaseUnavailable)
    @app.errorhandler(ServerSelectionTimeoutError)
    @app.errorhandler(ConnectionFailure)
    def database_unavailable(e):
        logger.error("Database unavailable: %s", e)
        return _error("DB_UNAVAILABLE", "Database unavailable", 503)

    @app.errorhandler(DuplicateKeyError)
    def duplicate_key(e):
        return _error("DUPLICATE", "This record already exists", 409)

    codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        415: "UNSUPPORTED_MEDIA_TYPE",
        429: "TOO_MANY_REQUESTS",
    }

    @app.errorhandler(HTTPException)
    def http_error(e):
        status = e.code or 500
        if status >= 500:
            return _error("INTERNAL_SERVER_ERROR", "An unexpected error occurred.", status)
        return _error(codes.get(status, "HTTP_ERROR"), e.description, status)

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.exception("Unhandled exception: %s", e)
        return _error("INTERNAL_SERVER_ERROR", "An unexpected error occurred.", 500)

    return app