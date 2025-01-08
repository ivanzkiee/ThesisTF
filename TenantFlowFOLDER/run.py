import os
import click
from flask.cli import FlaskGroup
from flask import Flask
from extensions import db

# Disable debugging tools and cache
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'
os.environ['FLASK_ENV'] = 'production'

from app import create_app

app = create_app()
cli = FlaskGroup(app)

def reset_database():
    """Helper function to reset the database"""
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Database has been reset successfully!")

@cli.command('reset-db')
def reset_db_command():
    """Reset the database from command line"""
    if click.confirm('Are you sure you want to reset the database? All data will be lost!', abort=True):
        reset_database()

if __name__ == '__main__':
    try:
        # Always reset database on startup to ensure correct schema
        reset_database()
        
        print("Starting Flask server...")
        app.run(
            host=app.config.get('HOST', '127.0.0.1'),
            port=app.config.get('PORT', 5000),
            debug=app.config.get('DEBUG', False)
        )
    except Exception as e:
        print(f"Error starting server: {e}") 