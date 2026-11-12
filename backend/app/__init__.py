from flask import Flask, jsonify
from flask_cors import CORS
from .config import Config
from .extensions import mongo

def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    mongo.init_app(app)

    from .blueprints.health.routes import health_bp
    app.register_blueprint(health_bp)

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"success": False, "error": {"code": "BAD_REQUEST", "message": str(e)}}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": str(e)}}), 401

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": str(e)}}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success": False, "error": {"code": "METHOD_NOT_ALLOWED", "message": str(e)}}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"success": False, "error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."}}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        import logging
        logging.exception("Unhandled exception: %s", e)
        return jsonify({"success": False, "error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."}}), 500

    return app
