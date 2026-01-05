from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from datetime import datetime

db = SQLAlchemy()
DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'CCAV@129'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # -------------------------------
    # ✅ JINJA FILTER: TIME AGO
    # -------------------------------
    @app.template_filter('timeago')
    def timeago(dt):
        if dt is None:
            return ""

        now = datetime.utcnow()
        diff = now - dt

        seconds = diff.total_seconds()
        minutes = seconds // 60
        hours = minutes // 60
        days = diff.days

        if seconds < 60:
            return "just now"
        elif minutes < 60:
            return f"{int(minutes)} min ago"
        elif hours < 24:
            return f"{int(hours)} hours ago"
        elif days < 7:
            return f"{days} day ago" if days == 1 else f"{days} days ago"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week ago" if weeks == 1 else f"{weeks} weeks ago"
        elif days < 365:
            months = days // 30
            return f"{months} month ago" if months == 1 else f"{months} months ago"
        else:
            years = days // 365
            return f"{years} year ago" if years == 1 else f"{years} years ago"

    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User, Post, Comment, Like
    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app
    @app.context_processor
    def inject_admin_flag():
        return dict(is_admin=session.get('is_admin', False))



def create_database(app):
    with app.app_context():
        db_path = path.join(app.root_path, DB_NAME)
        if not path.exists(db_path):
            db.create_all()
            print('Database Created Successfully!')
        else:
            print('Database already exists.')
