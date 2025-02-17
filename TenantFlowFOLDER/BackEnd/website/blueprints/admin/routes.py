from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ...models import User, Payment, MaintenanceRequest, Note, Notification
from ...extensions import db
from datetime import datetime, timedelta
from .utils import get_admin_statistics  # Import the function
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_authenticated or current_user.user_type != 'admin':
        flash('Access denied. Admin access only.', 'error')
        return redirect(url_for('auth.login'))

    try:
        # Get statistics
        stats = {
            'total_tenants': User.query.filter_by(user_type='tenant').count(),
            'monthly_payments': float(Payment.query.filter(
                Payment.status == 'paid',
                Payment.payment_date >= datetime.utcnow().replace(day=1)
            ).with_entities(func.sum(Payment.amount)).scalar() or 0),
            'pending_payments': Payment.query.filter_by(status='pending').count(),
            'overdue_payments': Payment.query.filter(
                Payment.status == 'pending',
                Payment.due_date < datetime.utcnow()
            ).count()
        }

        # Get payment data for chart
        last_6_months = [(datetime.utcnow() - timedelta(days=x*30)) for x in range(6)]
        payment_labels = [date.strftime('%B %Y') for date in reversed(last_6_months)]
        
        payment_data = {
            'paid': [],
            'pending': [],
            'overdue': []
        }

        for month in reversed(last_6_months):
            month_start = month.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            
            payment_data['paid'].append(
                Payment.query.filter(
                    Payment.status == 'paid',
                    Payment.payment_date.between(month_start, month_end)
                ).count()
            )
            
            payment_data['pending'].append(
                Payment.query.filter(
                    Payment.status == 'pending',
                    Payment.due_date.between(month_start, month_end)
                ).count()
            )
            
            payment_data['overdue'].append(
                Payment.query.filter(
                    Payment.status == 'pending',
                    Payment.due_date < month_end,
                    Payment.due_date >= month_start
                ).count()
            )

        # Get admin notes
        admin_notes = Note.query.filter_by(
            created_by=current_user.id
        ).order_by(Note.date.desc()).all()

        return render_template(
            'admin/admin_dashboard.html',
            stats=stats,
            payment_labels=payment_labels,
            payment_data=payment_data,
            admin_notes=admin_notes
        )
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard data', 'error')
        return redirect(url_for('views.home'))

# Helper functions for stats
def get_monthly_revenue():
    # Implementation
    pass

def get_payment_count(status):
    # Implementation
    pass

def get_payment_months():
    # Implementation
    pass

def get_payment_values():
    # Implementation
    pass

def get_occupancy_months():
    # Implementation
    pass

def get_occupancy_data():
    # Implementation
    pass

def get_tenant_notes():
    # Implementation
    pass

def get_tenant_payments():
    # Implementation
    pass

# CRUD endpoints for notes
@admin_bp.route('/note', methods=['POST'])
@login_required
def create_note():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.form
    note = Note(
        user_id=data.get('user_id'),
        data=data.get('content'),
        created_by=current_user.id
    )
    db.session.add(note)
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/note/<int:id>', methods=['GET', 'DELETE'])
@login_required
def manage_note(id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    note = Note.query.get_or_404(id)
    
    if request.method == 'GET':
        return jsonify({
            'id': note.id,
            'content': note.content,
            'tenant_id': note.tenant_id
        })
    
    if request.method == 'DELETE':
        db.session.delete(note)
        db.session.commit()
        return jsonify({'success': True})

@admin_bp.route('/payment/<int:id>')
@login_required
def view_payment(id):
    if current_user.user_type != 'admin':
        return redirect(url_for('views.home'))
    
    payment = Payment.query.get_or_404(id)
    return render_template('admin/review_payment.html', payment=payment)

@admin_bp.route('/send-warning/<int:tenant_id>', methods=['POST'])
@login_required
def send_payment_warning(tenant_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    tenant = User.query.get_or_404(tenant_id)
    
    # Create notification
    notification = Notification(
        user_id=tenant_id,
        title='Payment Warning',
        message=data.get('message'),
        type='warning',
        created_by=current_user.id
    )
    
    # Create note for admin records
    note = Note(
        tenant_id=tenant_id,
        content=f"Payment Warning Sent: {data.get('message')}",
        note_type='warning',
        created_by=current_user.id
    )
    
    db.session.add(notification)
    db.session.add(note)
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/approve-payment/<int:payment_id>', methods=['POST'])
@login_required
def approve_payment(payment_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    payment = Payment.query.get_or_404(payment_id)
    data = request.json
    
    payment.status = 'approved'
    payment.approved_by = current_user.id
    payment.approved_date = datetime.now()
    payment.admin_notes = data.get('notes')
    
    # Create notification for tenant
    notification = Notification(
        user_id=payment.tenant_id,
        title='Payment Approved',
        message=f'Your payment of ₱{payment.amount:,.2f} has been approved.',
        type='success'
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/add-note', methods=['POST'])
@login_required
def add_note():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    content = request.form.get('content')
    
    note = Note(
        data=content,
        created_by=current_user.id
    )
    
    db.session.add(note)
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/delete-note/<int:note_id>', methods=['DELETE'])
@login_required
def delete_note(note_id):
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    note = Note.query.get_or_404(note_id)
    if note.created_by != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    db.session.delete(note)
    db.session.commit()
    
    return jsonify({'success': True})