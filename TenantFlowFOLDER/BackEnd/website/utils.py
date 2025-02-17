import json
from datetime import datetime, timedelta
from .models import Notification, Payment, User, MaintenanceRequest, Message
from flask import current_app
from . import db
from werkzeug.security import generate_password_hash

def create_payment_reminder(user_id, amount_due, due_date):
    """
    Create payment reminder notification
    Args:
        user_id (int): ID of user to notify
        amount_due (float): Amount due for payment
        due_date (datetime): Payment due date
    """
    message = f"Payment reminder: ₱{amount_due:.2f} due on {due_date.strftime('%B %d, %Y')}"
    notification = Notification(
        user_id=user_id,
        message=message,
        type="payment_reminder"
    )
    return notification

def check_overdue_payments():
    """
    Check for overdue payments and create notifications
    Returns:
        list: List of created notifications
    """
    notifications = []
    today = datetime.utcnow()
    
    try:
        # Get pending payments
        upcoming_payments = Payment.query.filter(
            Payment.status == "pending"
        ).all()
        
        for payment in upcoming_payments:
            try:
                tenant = User.query.get(payment.tenant_id)
                if not tenant:
                    print(f"No tenant found for payment {payment.id}")
                    continue

                # Skip if no due date
                if not payment.due_date:
                    print(f"No due date for payment {payment.id}")
                    continue

                days_until_due = (payment.due_date - today).days
                
                if days_until_due <= 0:
                    message = (
                        f"OVERDUE: Payment of {format_currency(payment.amount)} "
                        f"was due on {payment.due_date.strftime('%B %d, %Y')}"
                    )
                elif days_until_due <= 5:  # Only notify for upcoming 5 days
                    message = (
                        f"Upcoming payment: {format_currency(payment.amount)} "
                        f"due in {days_until_due} days"
                    )
                else:
                    continue  # Skip if due date is more than 5 days away
                    
                notification = Notification(
                    user_id=tenant.id,
                    message=message,
                    type="payment_reminder"
                )
                notifications.append(notification)
                
            except Exception as e:
                print(f"Error processing payment {payment.id}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error in check_overdue_payments: {str(e)}")
        
    return notifications

def format_currency(amount):
    """
    Format currency amount with peso sign and proper decimal places
    Args:
        amount (float): Amount to format
    Returns:
        str: Formatted currency string
    """
    return f"₱{amount:,.2f}"

def get_maintenance_status_color(status):
    """
    Get bootstrap color class for maintenance status
    Args:
        status (str): Maintenance request status
    Returns:
        str: Bootstrap color class
    """
    status_colors = {
        'pending': 'warning',
        'in_progress': 'info',
        'completed': 'success',
        'cancelled': 'danger'
    }
    return status_colors.get(status, 'secondary')

def get_tenant_activities(tenant_id):
    """Get recent activities for a tenant"""
    activities = []
    
    try:
        # Get recent payments
        payments = Payment.query.filter_by(tenant_id=tenant_id)\
            .order_by(Payment.created_date.desc())\
            .limit(5).all()
        
        for payment in payments:
            activities.append({
                'date': payment.created_date.strftime('%Y-%m-%d'),
                'type': 'Payment',
                'description': f'Payment of ₱{payment.amount:,.2f}',
                'status': payment.status,
                'status_color': 'success' if payment.status == 'paid' 
                               else 'warning' if payment.status == 'pending' 
                               else 'danger'
            })

        # Get recent maintenance requests
        maintenance = MaintenanceRequest.query.filter_by(tenant_id=tenant_id)\
            .order_by(MaintenanceRequest.created_date.desc())\
            .limit(5).all()
        
        for request in maintenance:
            activities.append({
                'date': request.created_date.strftime('%Y-%m-%d'),
                'type': 'Maintenance',
                'description': request.description[:50] + '...' if len(request.description) > 50 else request.description,
                'status': request.status,
                'status_color': 'success' if request.status == 'completed' 
                               else 'info' if request.status == 'in_progress' 
                               else 'warning'
            })

        # Get recent complaints
        complaints = Message.query.filter_by(
            sender_id=tenant_id,
            message_type='complaint'
        ).order_by(Message.created_date.desc()).limit(5).all()
        
        for complaint in complaints:
            activities.append({
                'date': complaint.created_date.strftime('%Y-%m-%d'),
                'type': 'Complaint',
                'description': complaint.subject,
                'status': 'Read' if complaint.is_read else 'Unread',
                'status_color': 'success' if complaint.is_read else 'warning'
            })

        # Sort all activities by date
        activities.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'), reverse=True)
        
        return activities[:10]  # Return only the 10 most recent activities
        
    except Exception as e:
        print(f"Error getting tenant activities: {str(e)}")
        return [] 

def create_admin_user():
    """Create admin user if it doesn't exist"""
    from .models import User
    
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            email='admin@example.com',
            first_name='Admin',
            last_name='Administrator',
            password=generate_password_hash('Admin123!', method='sha256'),  # Stronger password
            user_type='admin',
            phone='09123456789',
            address='Agustin and Son Realty Office',
            emergency_contact_name='System Administrator',
            emergency_contact_phone='09123456789'
        )
        db.session.add(admin)
        db.session.commit() 