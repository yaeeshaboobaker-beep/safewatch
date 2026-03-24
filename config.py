import os
from dotenv import load_dotenv


load_dotenv()

class Config:
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-secret-key-if-env-fails'
    
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'safewatch.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = os.environ.get('EMAIL_PASS')