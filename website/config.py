import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # We will still enforce the fail-fast check for this in __init__.py
    SECRET_KEY = os.getenv('SECRET_KEY') 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ⚡ PERFORMANCE: Cache Static Files (Images/CSS) for 1 Year
    SEND_FILE_MAX_AGE_DEFAULT = 31536000
    
    # ==========================================
    # 📧 DYNAMIC EMAIL CONFIGURATION
    # ==========================================
    # Pulls directly from .env (Prevents accidental fallback to Gmail)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.zoho.in')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
    MAIL_USE_TLS = str(os.getenv('MAIL_USE_TLS', 'False')).lower() == 'true'
    MAIL_USE_SSL = str(os.getenv('MAIL_USE_SSL', 'True')).lower() == 'true'
    
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_USERNAME')

    # 🚀 DEDICATED ROUTING EMAILS
    SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'varshneyanurag888@gmail.com')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'anuragvarshney@zohomail.in')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    # SQLite does NOT support connection pooling — remove pool options in dev
    SQLALCHEMY_ENGINE_OPTIONS = {}

class ProductionConfig(Config):
    DEBUG = False
    # Use external DB in prod, fallback to sqlite if missing
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///database.db')
    # PostgreSQL/MySQL pooling options
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}