from flask import Flask
from os import path
from flask_login import LoginManager
0.
from .extensions import db, login_manager

# Initialize extensions
DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    
    # Configure login manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Import all models to ensure they're registered with SQLAlchemy
    from .models import User, Note, Unit, Payment, MaintenanceRequest, Notification, Message, CalendarEvent

    # Create database
    with app.app_context():
        db.create_all()
        print("Database created!")

    # Register blueprints
    from .views import views
    from .auth import auth
    from .blueprints.admin.routes import admin_bp
    from .blueprints.admin.unit_management import unit_management

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(unit_management, url_prefix='/')

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # Register the currency filter
    @app.template_filter('format_currency')
    def format_currency_filter(value):
        if value is None:
            return "₱0.00"
        try:
            value = float(value)
            if value == 0:
                return "₱0.00"
            return f"₱{value:,.2f}"
        except (ValueError, TypeError):
            return "₱0.00"

    return app

def create_database(app):
    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')