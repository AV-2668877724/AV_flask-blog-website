from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path, makedirs
from flask_login import LoginManager, current_user
from datetime import datetime


db = SQLAlchemy()
DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'CCAV@129'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # -------------------------------------------------
    # CONFIG: UPLOAD FOLDER
    # -------------------------------------------------
    UPLOAD_FOLDER = path.join(app.root_path, 'static', 'uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    # Create the folder if it doesn't exist
    if not path.exists(UPLOAD_FOLDER):
        makedirs(UPLOAD_FOLDER)

    db.init_app(app)

    # -------------------------------------------------
    # BLUEPRINTS
    # -------------------------------------------------
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    # -------------------------------------------------
    # MODELS & DB CREATION
    # -------------------------------------------------
    # Import models here to ensure they are registered with SQLAlchemy
    from .models import User, Post, Comment, Like, Notification, Follow
    
    create_database(app)

    # -------------------------------------------------
    # LOGIN MANAGER
    # -------------------------------------------------
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # -------------------------------------------------
    # CONTEXT PROCESSORS (Global Variables)
    # -------------------------------------------------
    
    @app.context_processor
    def inject_notifications():
        """
        Injects 'unread_count' and 'latest_notifs' into every template.
        Includes logic to prevent circular imports.
        """
        unread_count = 0
        latest_notifs = []
        
        if current_user.is_authenticated:
            # ✅ SAFE IMPORT: Import inside function to prevent crash
            from .models import Notification
            
            # 1. Get Count of Unread
            unread_count = Notification.query.filter_by(
                recipient_id=current_user.id, 
                is_read=False
            ).count()
            
            # 2. Get the actual latest 5 notifications for the dropdown
            latest_notifs = Notification.query.filter_by(recipient_id=current_user.id)\
                .order_by(Notification.date_created.desc())\
                .limit(5)\
                .all()
                
        return dict(unread_count=unread_count, latest_notifs=latest_notifs)

    @app.context_processor
    def inject_global_user():
        return dict(current_user=current_user)
        
    @app.context_processor
    def inject_admin_flag():
        # Safe check in case user is not logged in or doesn't have attribute
        is_admin = False
        if current_user.is_authenticated:
            is_admin = getattr(current_user, "is_admin", False)
        return dict(is_admin=is_admin)

    # -------------------------------------------------
    # JINJA FILTER: TIME AGO
    # -------------------------------------------------
    @app.template_filter('timeago')
    def timeago(dt):
        if dt is None: return ""
        now = datetime.utcnow()
        diff = now - dt
        seconds = diff.total_seconds()
        minutes = seconds // 60
        hours = minutes // 60
        days = diff.days
        if seconds < 60: return "just now"
        elif minutes < 60: return f"{int(minutes)} min ago"
        elif hours < 24: return f"{int(hours)} hours ago"
        elif days < 7: return f"{days} day ago" if days == 1 else f"{days} days ago"
        elif days < 30: 
            weeks = days // 7
            return f"{weeks} week ago" if weeks == 1 else f"{weeks} weeks ago"
        elif days < 365:
            months = days // 30
            return f"{months} month ago" if months == 1 else f"{months} months ago"
        else:
            return dt.strftime('%Y-%m-%d')

    return app

def create_database(app):
    with app.app_context():
        db_path = path.join(app.root_path, DB_NAME)
        if not path.exists(db_path):
            db.create_all()
            print('Database Created Successfully!')