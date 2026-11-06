"""Flask application factory."""
from flask import Flask
from app.config import Config
from app.database import db


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder='../static', template_folder='../templates')

    # Load configuration
    app.config.from_object(config_class)

    # Initialize database
    db.init_app(app)

    # Register blueprints
    from app.routes import projects, documents, search, todos
    app.register_blueprint(projects.bp)
    app.register_blueprint(documents.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(todos.bp)

    # Main route
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Resource not found'}, 404

    @app.errorhandler(500)
    def internal_error(e):
        return {'error': 'Internal server error'}, 500

    return app
