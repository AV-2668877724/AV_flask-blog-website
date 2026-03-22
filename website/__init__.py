from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path, makedirs
from flask_login import LoginManager, current_user
from flask_mail import Mail
import os
from datetime import datetime
from flask_socketio import SocketIO
from flask_compress import Compress
from sqlalchemy.orm import joinedload 
from flask_wtf.csrf import CSRFProtect 

# 🚀 NEW: Import Flask-Limiter for Spam Protection
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
mail = Mail()
DB_NAME = "database.db"
socketio = SocketIO() 
csrf = CSRFProtect() 

# 🚀 NEW: Initialize Limiter globally
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"], # Global fallback limit
    storage_uri="memory://" # Uses local memory, perfect for a single-server setup
)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ⚡ PERFORMANCE: Cache Static Files (Images/CSS) for 1 Year
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000
    
    # ⚡ PERFORMANCE: Database Connection Pooling
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 20,       
        'pool_recycle': 3600,  
        'pool_pre_ping': True  
    }
    
    # EMAIL CONFIGURATION
    app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')    
    
    mail.init_app(app)
    
    # ⚡ PERFORMANCE: Enable Gzip Compression
    Compress(app) 
    
    # UPLOAD FOLDER
    UPLOAD_FOLDER = path.join(app.root_path, 'static', 'uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    if not path.exists(UPLOAD_FOLDER):
        makedirs(UPLOAD_FOLDER)

    db.init_app(app)
    socketio.init_app(app)
    csrf.init_app(app) 
    
    # 🚀 NEW: Bind Limiter to the App
    limiter.init_app(app)

    # BLUEPRINTS
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    # DB CREATION
    from .models import User, Post, Comment, Like, Notification, Follow, Message, SavedPost
    create_database(app)

    # LOGIN MANAGER
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # CONTEXT PROCESSORS
    @app.context_processor
    def inject_notifications():
        unread_notifs = 0
        unread_messages = 0 
        latest_notifs = []
        
        if current_user.is_authenticated:
            try:
                unread_notifs = Notification.query.filter_by(
                    recipient_id=current_user.id, is_read=False).count()
                
                unread_messages = Message.query.filter_by(
                    recipient_id=current_user.id, is_read=False).count()
                
                latest_notifs = Notification.query.options(joinedload(Notification.visitor)).filter_by(recipient_id=current_user.id)\
                    .order_by(Notification.date_created.desc()).limit(5).all()
            except:
                pass 
        
        return dict(
            unread_count=unread_notifs, 
            unread_messages=unread_messages, 
            latest_notifs=latest_notifs,
            now=datetime.utcnow() 
        )

    @app.context_processor
    def inject_admin_flag():
        is_admin = False
        if current_user.is_authenticated:
            is_admin = getattr(current_user, "is_admin", False)
        return dict(is_admin=is_admin)

    # JINJA FILTERS
    @app.template_filter('timeago')
    def timeago(dt):
        if dt is None: return ""
        now = datetime.utcnow() 
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        
        diff = now - dt
        seconds = diff.total_seconds()
        
        if seconds < 0: return "just now"

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

    from . import events
    
    return app

def create_database(app):
    with app.app_context():
        db_path = path.join(app.root_path, DB_NAME)
        if not path.exists(db_path):
            db.create_all()
            print('Database Created Successfully!')