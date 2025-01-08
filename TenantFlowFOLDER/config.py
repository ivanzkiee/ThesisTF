import os

class Config:
    # Database configuration
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security
    SECRET_KEY = 'your-secret-key-here'
    
    # Debug settings
    DEBUG = False
    TESTING = False
    
    # Server settings
    HOST = '0.0.0.0'
    PORT = 5000
