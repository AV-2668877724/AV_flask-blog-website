from flask import Flask, url_for 
from flask_sqlalchemy import SQLAlchemy
from os import path, makedirs
from flask_login import LoginManager, current_user
from flask_mail import Mail
import os
from datetime import datetime, timezone
from flask_socketio import SocketIO
from flask_compress import Compress
from sqlalchemy.orm import joinedload 
from flask_wtf.csrf import CSRFProtect 

from .config import config

# 🚀 Imports for Spam Protection & Migrations
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

db = SQLAlchemy()
mail = Mail()
DB_NAME = "database.db"

socketio = SocketIO() 
csrf = CSRFProtect() 

# Initialize Limiter and Migrate globally
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"], 
    storage_uri="memory://" 
)
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # 🚀 NEW: Load Config via Environment Split
    env = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[env])

    # 🚀 SECURITY UPDATE: Secure SECRET_KEY fallback (Fail-Fast)
    if not app.config.get('SECRET_KEY'):
        raise RuntimeError("SECRET_KEY environment variable is not set! Create a .env file.")

    # 🚀 FIX: FORCE MAIL CONFIGURATION FROM .ENV
    # This prevents the app from falling back to default Gmail settings in config.py
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
    app.config['MAIL_USE_TLS'] = str(os.getenv('MAIL_USE_TLS', 'False')).lower() == 'true'
    app.config['MAIL_USE_SSL'] = str(os.getenv('MAIL_USE_SSL', 'True')).lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

    # ==========================================
    # 🛡️ HARDENED SECURITY CONFIGURATION
    # ==========================================
    # 1. Protect Cookies from JavaScript (Stops XSS session theft)
    app.config['SESSION_COOKIE_HTTPONLY'] = True

    # 2. Only send cookies over HTTPS (Prevents Wi-Fi snooping)
    is_production = os.getenv('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_SECURE'] = is_production 

    # 3. Stop cross-site cookie sending (Extra CSRF protection)
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' 

    mail.init_app(app)
    
    # ⚡ PERFORMANCE: Enable Gzip Compression
    Compress(app)
    
    # UPLOAD FOLDER
    UPLOAD_FOLDER = path.join(app.root_path, 'static', 'uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    # Tell CSRF protection to trust ngrok URLs
    app.config['WTF_CSRF_TRUSTED_ORIGINS'] = [
        'https://*.ngrok-free.app',
        'https://*.ngrok.app',
        'https://*.ngrok.io'
    ]
    
    if not path.exists(UPLOAD_FOLDER):
        makedirs(UPLOAD_FOLDER)

    db.init_app(app)
    csrf.init_app(app) 
    limiter.init_app(app)
    
    # ==========================================
    # 🚀 ULTIMATE WEBSOCKET SECURITY & SPEED FIX
    # ==========================================
    public_domain = os.getenv("PUBLIC_DOMAIN")

    if is_production and public_domain:
        allowed_origins = [public_domain] # Strict security for launch
    else:
        allowed_origins = "*" # Open door for Ngrok testing so it stays fast!

    socketio.init_app(app, cors_allowed_origins=allowed_origins)
    
    # 🚀 NEW: Bind Migrate to the App and Database
    migrate.init_app(app, db)

    # BLUEPRINTS
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    # DB CREATION (Import models so Alembic can see them)
    from .models import User, Post, Comment, Like, Notification, Follow, Message, SavedPost, Block, Report
    
    # LOGIN MANAGER
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # ==========================================
    # 🛡️ SECURITY HEADERS (Clickjacking & XSS Protection)
    # ==========================================
    @app.after_request
    def add_security_headers(response):
        """Adds mandatory security headers to every HTTP response."""
        # Prevent browsers from guessing the file type (Stops MIME-sniffing exploits)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent your site from being put in an iframe (Stops Clickjacking)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Force the browser to turn on its built-in XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Force all future connections to be HTTPS only (HSTS)
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response

    # ==========================================
    # CONTEXT PROCESSORS
    # ==========================================
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
            now=datetime.now(timezone.utc).replace(tzinfo=None),
            # 🚀 NEW: Dynamically inject BOTH support and admin emails globally!
            support_email=os.getenv('SUPPORT_EMAIL', 'varshneyanurag888@gmail.com'),
            admin_email=os.getenv('ADMIN_EMAIL', 'anuragvarshney@zohomail.in')
        )

    @app.context_processor
    def inject_admin_flag():
        is_admin = False
        if current_user.is_authenticated:
            is_admin = getattr(current_user, "is_admin", False)
        return dict(is_admin=is_admin)

    # 🚀 Automated Cache Busting
    @app.context_processor
    def override_url_for():
        def dated_url_for(endpoint, **values):
            if endpoint == 'static':
                filename = values.get('filename', None)
                if filename:
                    # Find the physical file and append its last modified time as ?v=...
                    file_path = os.path.join(app.root_path, endpoint, filename)
                    if os.path.isfile(file_path):
                        values['v'] = int(os.stat(file_path).st_mtime)
            return url_for(endpoint, **values)
        return dict(url_for=dated_url_for)

    # ==========================================
    # JINJA FILTERS
    # ==========================================
    @app.template_filter('timeago')
    def timeago(dt):
        if dt is None: return ""
        now = datetime.now(timezone.utc).replace(tzinfo=None) 
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