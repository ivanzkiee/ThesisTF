from .extensions import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))  # This will store the note content
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    note_type = db.Column(db.String(50), default='general')


class UserType(Enum):
    ADMIN = "admin"
    TENANT = "tenant"
    MAINTENANCE = "maintenance"

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    emergency_contact_name = db.Column(db.String(150))
    emergency_contact_phone = db.Column(db.String(20))
    user_type = db.Column(db.String(20), default='tenant')
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    unit_number = db.Column(db.String(50))
    balance = db.Column(db.Float, default=0.0)

    # Relationships
    user_notes = db.relationship('Note', 
                               foreign_keys='Note.user_id',
                               backref='user_note',
                               lazy=True)
    authored_notes = db.relationship('Note', 
                                   foreign_keys='Note.created_by',
                                   backref='author',
                                   lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    payments = db.relationship('Payment', 
                             foreign_keys='Payment.tenant_id',
                             backref='payment_tenant',
                             lazy=True)
    maintenance_requests = db.relationship('MaintenanceRequest', 
                                        foreign_keys='MaintenanceRequest.tenant_id',
                                        backref='requester',
                                        lazy=True)
    assigned_maintenance = db.relationship('MaintenanceRequest',
                                         foreign_keys='MaintenanceRequest.assigned_to',
                                         backref='assigned_to_user',
                                         lazy=True)
    calendar_events = db.relationship('CalendarEvent', backref='creator', lazy=True)
    messages_sent = db.relationship('Message', 
                                  foreign_keys='Message.sender_id',
                                  backref='sender',
                                  lazy='dynamic')
    messages_received = db.relationship('Message',
                                      foreign_keys='Message.receiver_id',
                                      backref='receiver',
                                      lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_number = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(50))  # vacant/occupied/maintenance
    floor = db.Column(db.Integer)
    building = db.Column(db.String(150))
    current_tenant_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    rent_amount = db.Column(db.Float)
    last_maintenance_date = db.Column(db.DateTime)
    tenant = db.relationship('User', foreign_keys=[current_tenant_id])
    maintenance_requests = db.relationship('MaintenanceRequest', backref='unit', lazy=True)

class MaintenanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    tenant_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    description = db.Column(db.String(500))
    category = db.Column(db.String(50))
    priority = db.Column(db.String(50))  # low, medium, high
    status = db.Column(db.String(50))  # pending, in_progress, completed
    photos = db.Column(db.String(500))  # Comma-separated photo filenames
    resolution = db.Column(db.String(500))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    completed_date = db.Column(db.DateTime)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))

    # No need to define relationships here as they're defined in User class with backrefs

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    tenant = db.relationship(
        'User', 
        foreign_keys=[tenant_id],
        backref=db.backref('tenant_payments', lazy=True),
        overlaps="payment_tenant,payments"
    )
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='pending')  # paid, pending, overdue
    payment_method = db.Column(db.String(50))
    reference_number = db.Column(db.String(100))
    proof_of_payment = db.Column(db.String(200))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    message = db.Column(db.String(500))
    type = db.Column(db.String(50))  # payment_reminder, maintenance, announcement
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    all_day = db.Column(db.Boolean, default=True)
    event_type = db.Column(db.String(50))  # complaint, maintenance, payment, general
    description = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=True)
    status = db.Column(db.String(50), default='pending')  # pending, resolved, cancelled
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject = db.Column(db.String(200))
    content = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    message_type = db.Column(db.String(50))  # complaint, inquiry, general
    attachment = db.Column(db.String(200), nullable=True)  # For any attached files

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # payment, maintenance, announcement, urgent
    status = db.Column(db.String(50), default='pending')  # pending, sent, cancelled
    recipients = db.Column(db.String(200))  # Comma-separated list or JSON string
    notification_methods = db.Column(db.String(200))  # JSON string of enabled methods
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_date = db.Column(db.DateTime, nullable=True)
    sent_date = db.Column(db.DateTime, nullable=True)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_name = db.Column(db.String(200))
    business_address = db.Column(db.String(200))
    contact_email = db.Column(db.String(150))
    contact_phone = db.Column(db.String(50))
    currency_symbol = db.Column(db.String(10), default='₱')
    
    # Payment Settings
    late_payment_fee = db.Column(db.Float, default=0.0)
    grace_period = db.Column(db.Integer, default=3)
    accept_cash = db.Column(db.Boolean, default=True)
    accept_bank_transfer = db.Column(db.Boolean, default=True)
    accept_gcash = db.Column(db.Boolean, default=True)
    
    # Notification Settings
    payment_reminder_email = db.Column(db.Boolean, default=True)
    payment_reminder_sms = db.Column(db.Boolean, default=False)
    reminder_days = db.Column(db.Integer, default=5)
    
    # Security Settings
    two_factor_enabled = db.Column(db.Boolean, default=False)
    login_notifications = db.Column(db.Boolean, default=True)
    last_backup_date = db.Column(db.DateTime)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False)  # low, medium, high
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, resolved
    admin_reply = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_date = db.Column(db.DateTime)
    
    # Update the relationship to reference the correct table name
    tenant = db.relationship('User', backref='complaints', foreign_keys=[tenant_id])

