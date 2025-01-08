from website import create_app
from website.models import db, User
import os
from dotenv import load_dotenv

load_dotenv()

app = create_app()

# Initialize database and admin user
with app.app_context():
    db.create_all()
    
    # Create default admin if it doesn't exist
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            email='admin@example.com',
            first_name='Admin',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)