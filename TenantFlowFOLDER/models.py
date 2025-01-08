from extensions import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def create_user(username, email):
        try:
            user = User(username=username, email=email)
            db.session.add(user)
            db.session.commit()
            return user, None
        except IntegrityError as e:
            db.session.rollback()
            return None, "Email already exists"
        except Exception as e:
            db.session.rollback()
            return None, str(e)