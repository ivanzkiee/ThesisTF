from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    due_date = db.Column(db.DateTime)
    priority = db.Column(db.Integer)  # 1-5 for priority levels


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    profile_pic = db.Column(db.String(200))
    unit_number = db.Column(db.String(20))
    lease_start = db.Column(db.DateTime)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.relationship('Note')
    payments = db.relationship('Payment', backref='user', lazy=True)
    role = db.Column(db.String(20), default='tenant')  # 'admin' or 'tenant'
    is_active = db.Column(db.Boolean, default=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def delete_user(self):
        # Delete all notes associated with the user
        Note.query.filter_by(user_id=self.id).delete()
        # Delete all categories associated with the user
        Category.query.filter_by(user_id=self.id).delete()
        # Delete the user
        db.session.delete(self)
        db.session.commit()

    def get_total_paid(self, year=None):
        query = Payment.query.filter_by(user_id=self.id, status='paid')
        if year:
            query = query.filter(db.extract('year', Payment.date) == year)
        return sum(payment.amount for payment in query.all())

    def get_next_payment_due(self):
        return Payment.query.filter_by(
            user_id=self.id, 
            status='pending'
        ).order_by(Payment.date).first()

    def get_outstanding_balance(self):
        pending_payments = Payment.query.filter_by(
            user_id=self.id, 
            status='pending'
        ).all()
        return sum(payment.amount for payment in pending_payments)

    def is_admin(self):
        return self.role == 'admin'

    def is_tenant(self):
        return self.role == 'tenant'

    def can_login(self):
        return self.is_active or self.is_admin()

    def unread_notifications_count(self):
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue
    reference = db.Column(db.String(50), unique=True)
    method = db.Column(db.String(50))  # gcash, bank_transfer, cash, credit_card
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receipt_url = db.Column(db.String(200))
    notes = db.Column(db.String(500))

    def generate_reference(self):
        return f"INV-{self.date.strftime('%Y%m')}-{self.id:04d}"

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'date': self.date.strftime('%Y-%m-%d'),
            'status': self.status,
            'reference': self.reference,
            'method': self.method
        }


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(100))
    message = db.Column(db.String(500))
    type = db.Column(db.String(50))  # 'payment_reminder', 'general', etc.
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'date': self.date_created.strftime('%Y-%m-%d %H:%M'),
            'is_read': self.is_read
        }