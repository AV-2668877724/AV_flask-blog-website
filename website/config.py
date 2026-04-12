import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # We will still enforce the fail-fast check for this in __init__.py
    SECRET_KEY = os.getenv('SECRET_KEY') 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ⚡ PERFORMANCE: Cache Static Files (Images/CSS) for 1 Year
    SEND_FILE_MAX_AGE_DEFAULT = 31536000
    
    # EMAIL CONFIGURATION
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

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