import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours
    
    # Database
    # Use postgresql+psycopg for psycopg v3, or postgresql:// for psycopg2
    # Default to SQLite for development if DATABASE_URL not set
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Use SQLite for development
        SQLALCHEMY_DATABASE_URI = 'sqlite:///hsea_assistant.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Azure Speech Services
    AZURE_SPEECH_KEY = os.environ.get('AZURE_SPEECH_KEY')
    AZURE_SPEECH_REGION = os.environ.get('AZURE_SPEECH_REGION')
    
    # Zoom API
    ZOOM_CLIENT_ID = os.environ.get('ZOOM_CLIENT_ID')
    ZOOM_CLIENT_SECRET = os.environ.get('ZOOM_CLIENT_SECRET')
    ZOOM_ACCOUNT_ID = os.environ.get('ZOOM_ACCOUNT_ID')
    ZOOM_REDIRECT_URI = os.environ.get('ZOOM_REDIRECT_URI', 'http://localhost:5001/api/meetings/zoom/callback')
    
    # Twilio
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    
    # Firebase
    FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH')
    
    # Google Calendar
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    # Outlook Calendar
    OUTLOOK_CLIENT_ID = os.environ.get('OUTLOOK_CLIENT_ID')
    OUTLOOK_CLIENT_SECRET = os.environ.get('OUTLOOK_CLIENT_SECRET')
    
    # Email (SMTP) – Gmail, SendGrid, etc.
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or MAIL_USERNAME
    MAIL_TIMEOUT = int(os.environ.get('MAIL_TIMEOUT', 30))
    MAIL_DEBUG = os.environ.get('MAIL_DEBUG', 'false').lower() == 'true'
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'false').lower() == 'true'
    
    # File store (uploads directory, relative to app root)
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_MB', 16)) * 1024 * 1024  # 16 MB default
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # API Base URL
    # Default to port 5001 to avoid conflict with AirPlay on macOS
    default_port = os.environ.get('PORT', '5001')
    API_BASE_URL = os.environ.get('API_BASE_URL', f'http://localhost:{default_port}')
