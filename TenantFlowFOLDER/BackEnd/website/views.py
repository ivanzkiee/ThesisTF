from flask import Blueprint, render_template, request, flash, jsonify, send_file, redirect, url_for, g
from flask_login import login_required, current_user
from .models import *
from . import db
from .utils import (
    create_payment_reminder,
    check_overdue_payments,
    format_currency,
    get_maintenance_status_color,
    get_tenant_activities
)
from datetime import datetime, timedelta
from calendar import monthrange
from collections import defaultdict
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from sqlalchemy import case, func, extract
import json

views = Blueprint('views', __name__)

UPLOAD_FOLDER = 'website/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@views.route('/')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    if current_user.user_type == 'admin':
        return redirect(url_for('views.admin_dashboard'))
    return redirect(url_for('views.tenant_dashboard'))

@views.route('/notifications')
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).all()
    return jsonify([{
        'id': n.id,
        'message': n.message,
        'type': n.type,
        'created_date': n.created_date.strftime('%Y-%m-%d %H:%M:%S')
    } for n in notifications])

@views.route('/mark-notification-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 403

@views.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_type != 'admin':
        flash('Access denied. Admin access only.', 'error')
        return redirect(url_for('views.home'))
    if current_user.user_type == 'admin':
        return redirect(url_for('views.admin_dashboard'))
    else:
        flash('Unauthorized access. Redirecting to tenant dashboard.', 'warning')
        return redirect(url_for('views.tenant_dashboard'))

@views.route('/mark-payment-paid/<int:payment_id>', methods=['POST'])
@login_required
def mark_payment_paid(payment_id):
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    payment = Payment.query.get_or_404(payment_id)
    payment.status = 'paid'
    payment.payment_date = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})

@views.route('/submit-maintenance-request', methods=['POST'])
@login_required
def submit_maintenance_request():
    if current_user.user_type != 'tenant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    data = request.json
    unit = Unit.query.filter_by(current_tenant_id=current_user.id).first()
    
    if not unit:
        return jsonify({'success': False, 'error': 'No unit assigned'}), 400
        
    new_request = MaintenanceRequest(
        unit_id=unit.id,
        tenant_id=current_user.id,
        description=data.get('description'),
        priority=data.get('priority'),
        status='pending'
    )
    
    db.session.add(new_request)
    db.session.commit()
    return jsonify({'success': True})

@views.route('/update-maintenance-status/<int:request_id>', methods=['POST'])
@login_required
def update_maintenance_status(request_id):
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    request = MaintenanceRequest.query.get_or_404(request_id)
    data = request.json
    request.status = data.get('status')
    db.session.commit()
    return jsonify({'success': True})

@views.route('/calendar-events')
@login_required
def get_calendar_events():
    # Get date range from query parameters
    start = request.args.get('start', type=str)
    end = request.args.get('end', type=str)
    
    if current_user.user_type == 'admin':
        # Admins see all events
        events = CalendarEvent.query.filter(
            CalendarEvent.start_date >= start,
            CalendarEvent.start_date <= end
        ).all()
    else:
        # Tenants see only their events
        unit = Unit.query.filter_by(current_tenant_id=current_user.id).first()
        events = CalendarEvent.query.filter(
            CalendarEvent.start_date >= start,
            CalendarEvent.start_date <= end,
            db.or_(
                CalendarEvent.created_by == current_user.id,
                CalendarEvent.unit_id == unit.id if unit else None
            )
        ).all()
    
    return jsonify([{
        'id': event.id,
        'title': event.title,
        'start': event.start_date.isoformat(),
        'end': event.end_date.isoformat() if event.end_date else None,
        'allDay': event.all_day,
        'type': event.event_type,
        'status': event.status,
        'className': f'event-{event.event_type} status-{event.status}'
    } for event in events])

@views.route('/add-calendar-event', methods=['POST'])
@login_required
def add_calendar_event():
    data = request.json
    unit = Unit.query.filter_by(current_tenant_id=current_user.id).first() if current_user.user_type == 'tenant' else None
    
    event = CalendarEvent(
        title=data.get('title'),
        start_date=datetime.fromisoformat(data.get('start')),
        end_date=datetime.fromisoformat(data.get('end')) if data.get('end') else None,
        all_day=data.get('allDay', True),
        event_type=data.get('type', 'general'),
        description=data.get('description'),
        created_by=current_user.id,
        unit_id=unit.id if unit else None
    )
    
    db.session.add(event)
    
    # Create notification for complaints
    if event.event_type == 'complaint':
        notification = Notification(
            user_id=User.query.filter_by(user_type='admin').first().id,
            message=f"New complaint from {current_user.first_name} (Unit {unit.unit_number if unit else 'N/A'}): {event.title}",
            type='complaint'
        )
        db.session.add(notification)
    
    db.session.commit()
    return jsonify({'success': True, 'id': event.id})

@views.route('/tenant/dashboard')
@login_required
def tenant_dashboard():
    if current_user.user_type != 'tenant':
        return redirect(url_for('admin.dashboard'))
    
    # Get all units for availability display
    units = Unit.query.order_by(Unit.building, Unit.floor, Unit.unit_number).all()
    
    # Get tenant's payments
    payments = Payment.query.filter_by(
        tenant_id=current_user.id
    ).order_by(Payment.created_date.desc()).all()
    
    # Get unit information
    current_unit = Unit.query.filter_by(current_tenant_id=current_user.id).first()
    
    # Get maintenance requests
    maintenance_requests = MaintenanceRequest.query.filter_by(
        tenant_id=current_user.id
    ).order_by(MaintenanceRequest.created_date.desc()).limit(5).all()
    
    return render_template('tenant/tenant_dashboard.html',
                         payments=payments,
                         unit=current_unit,
                         units=units,
                         maintenance_requests=maintenance_requests)

@views.route('/tenant/payment')
@login_required
def make_payment():
    if current_user.user_type != 'tenant':
        flash('Unauthorized access', 'error')
        return redirect(url_for('views.home'))
    
    # Get tenant's payments
    payments = Payment.query.filter_by(
        tenant_id=current_user.id
    ).order_by(Payment.created_date.desc()).all()
    
    return render_template('tenant/payment_dashboard.html', payments=payments)

@views.route('/tenant/submit-payment', methods=['POST'])
@login_required
def submit_payment():
    if current_user.user_type != 'tenant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        amount = float(request.form.get('amount'))
        payment_method = request.form.get('payment_method')
        reference_number = request.form.get('reference_number')
        
        # Validate payment method requirements
        if payment_method in ['gcash', 'bank']:
            if not reference_number:
                return jsonify({
                    'success': False, 
                    'error': 'Reference number is required for GCash and Bank Transfer'
                })
            
            if 'proof_of_payment' not in request.files:
                return jsonify({
                    'success': False, 
                    'error': 'Proof of payment is required for GCash and Bank Transfer'
                })
        
        # Handle file upload
        proof_file = request.files.get('proof_of_payment')
        proof_filename = None
        
        if proof_file and proof_file.filename:
            filename = secure_filename(proof_file.filename)
            proof_filename = f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{filename}"
            
            # Create uploads directory if it doesn't exist
            os.makedirs('website/static/uploads/payments', exist_ok=True)
            proof_file.save(os.path.join('website/static/uploads/payments', proof_filename))
        
        # Create payment record
        payment = Payment(
            tenant_id=current_user.id,
            amount=amount,
            payment_method=payment_method,
            reference_number=reference_number,
            proof_of_payment=proof_filename,
            status='pending',
            created_date=datetime.utcnow()
        )
        
        db.session.add(payment)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Payment error: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while processing payment'})

@views.route('/tenant/cancel-payment/<int:payment_id>', methods=['POST'])
@login_required
def cancel_payment(payment_id):
    if current_user.user_type != 'tenant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        payment = Payment.query.get_or_404(payment_id)
        
        if payment.tenant_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if payment.status != 'pending':
            return jsonify({'success': False, 'error': 'Can only cancel pending payments'})
        
        # Delete proof of payment file if exists
        if payment.proof_of_payment:
            file_path = os.path.join('website/static/uploads/payments', payment.proof_of_payment)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        db.session.delete(payment)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Cancel payment error: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while canceling payment'})

@views.route('/tenant/payment-history')
@login_required
def payment_history():
    payments = Payment.query.filter_by(tenant_id=current_user.id).all()
    return render_template('payment_history.html', payments=payments)

@views.route('/tenant/maintenance')
@login_required
def maintenance_dashboard():
    if current_user.user_type != 'tenant':
        flash('Unauthorized access', 'error')
        return redirect(url_for('views.home'))
    
    # Get active and completed requests
    active_requests = MaintenanceRequest.query.filter_by(
        tenant_id=current_user.id
    ).filter(
        MaintenanceRequest.status != 'completed'
    ).order_by(MaintenanceRequest.created_date.desc()).all()
    
    completed_requests = MaintenanceRequest.query.filter_by(
        tenant_id=current_user.id,
        status='completed'
    ).order_by(MaintenanceRequest.created_date.desc()).all()
    
    return render_template('tenant/maintenance_dashboard.html',
                         active_requests=active_requests,
                         completed_requests=completed_requests)

@views.route('/tenant/submit-maintenance', methods=['POST'])
@login_required
def submit_maintenance():
    if current_user.user_type != 'tenant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        category = request.form.get('category')
        description = request.form.get('description')
        priority = request.form.get('priority')
        
        if not all([category, description, priority]):
            return jsonify({
                'success': False,
                'error': 'Please fill in all required fields'
            })
        
        # Handle photo uploads
        photos = []
        if 'photos' in request.files:
            uploaded_files = request.files.getlist('photos')
            for file in uploaded_files[:3]:  # Limit to 3 photos
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{filename}"
                    
                    # Create uploads directory if it doesn't exist
                    os.makedirs('website/static/uploads/maintenance', exist_ok=True)
                    file.save(os.path.join('website/static/uploads/maintenance', unique_filename))
                    photos.append(unique_filename)
        
        # Get tenant's unit
        unit = Unit.query.filter_by(current_tenant_id=current_user.id).first()
        
        # Create maintenance request
        maintenance_request = MaintenanceRequest(
            tenant_id=current_user.id,
            unit_id=unit.id if unit else None,
            category=category,
            description=description,
            priority=priority,
            photos=','.join(photos) if photos else None,
            status='pending',
            created_date=datetime.utcnow()
        )
        
        db.session.add(maintenance_request)
        
        # Create notifications for all admin users
        admin_users = User.query.filter_by(user_type='admin').all()
        for admin in admin_users:
            notification = Notification(
                user_id=admin.id,
                title='New Maintenance Request',
                message=f'New {priority} priority maintenance request from Unit {unit.unit_number if unit else "N/A"}: {category}',
                type='maintenance',
                created_date=datetime.utcnow()
            )
            db.session.add(notification)
        
        db.session.commit()
        
        # Send real-time notification (if you have WebSocket set up)
        # socketio.emit('new_maintenance_request', {
        #     'message': f'New {priority} priority maintenance request from Unit {unit.unit_number if unit else "N/A"}'
        # }, room='admin_room')
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Maintenance request error: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'An error occurred while submitting request'})

@views.route('/tenant/maintenance/<int:request_id>')
@login_required
def view_maintenance(request_id):
    if current_user.user_type != 'tenant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    request = MaintenanceRequest.query.get_or_404(request_id)
    if request.tenant_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    return jsonify({
        'category': request.category,
        'description': request.description,
        'priority': request.priority,
        'status': request.status,
        'created_date': request.created_date.strftime('%Y-%m-%d %H:%M'),
        'resolution': request.resolution,
        'photos': request.photos.split(',') if request.photos else []
    })

@views.route('/tenant/maintenance/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_maintenance(request_id):
    if current_user.user_type != 'tenant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        request = MaintenanceRequest.query.get_or_404(request_id)
        if request.tenant_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if request.status != 'pending':
            return jsonify({'success': False, 'error': 'Can only cancel pending requests'})
        
        # Delete photos if they exist
        if request.photos:
            for photo in request.photos.split(','):
                file_path = os.path.join('website/static/uploads/maintenance', photo)
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        db.session.delete(request)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Cancel maintenance error: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while canceling request'})

@views.route('/tenant/submit-complaint')
@login_required
def submit_complaint():
    # Get user's complaints history
    complaints = Complaint.query.filter_by(tenant_id=current_user.id)\
        .order_by(Complaint.created_date.desc()).all()
    return render_template('tenant/complaints.html', complaints=complaints)

@views.route('/tenant/submit-complaint/submit', methods=['POST'])
@login_required
def handle_complaint_submission():
    if request.method == 'POST':
        try:
            data = request.json
            new_complaint = Complaint(
                tenant_id=current_user.id,
                subject=data.get('subject'),
                description=data.get('description'),
                priority=data.get('priority'),
                status='pending'
            )
            
            db.session.add(new_complaint)
            
            # Create notification for admin
            admin_users = User.query.filter_by(user_type='admin').all()
            for admin in admin_users:
                notification = Notification(
                    user_id=admin.id,
                    title='New Complaint',
                    message=f'New {data.get("priority")} priority complaint from {current_user.first_name}: {data.get("subject")}',
                    type='complaint'
                )
                db.session.add(notification)
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
    return redirect(url_for('views.submit_complaint'))

@views.route('/tenant/submit-complaint/<int:complaint_id>/details')
@login_required
def complaint_details(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.tenant_id != current_user.id and current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    return jsonify({
        'subject': complaint.subject,
        'description': complaint.description,
        'status': complaint.status,
        'priority': complaint.priority,
        'created_date': complaint.created_date.strftime('%Y-%m-%d %H:%M'),
        'admin_reply': complaint.admin_reply
    })

@views.route('/tenant/notice-board')
@login_required
def notice_board():
    notices = Notification.query.filter_by(type='announcement').all()
    return render_template('notice_board.html', notices=notices)

@views.route('/tenant/move-out-notice', methods=['GET', 'POST'])
@login_required
def move_out_notice():
    return render_template('move_out_notice.html')

@views.route('/tenant/profile')
@login_required
def tenant_profile():
    return render_template('tenant_profile.html')

@views.route('/admin/manage-tenants')
@login_required
def manage_tenants():
    if current_user.user_type != 'admin':
        return redirect(url_for('views.home'))
        
    # Get all tenants
    tenants = User.query.filter_by(user_type='tenant').order_by(User.first_name).all()
    
    # Get all units organized by building
    units = Unit.query.order_by(Unit.building, Unit.floor, Unit.unit_number).all()
    
    # Organize units by building and floor
    buildings = ['A', 'B', 'C', 'D', 'E']
    floors = range(1, 6)  # 5 floors
    units_per_floor = 7
    
    organized_units = {}
    for building in buildings:
        organized_units[building] = {}
        for floor in floors:
            organized_units[building][floor] = []
            for unit in units:
                if unit.building == f'Building {building}' and unit.floor == floor:
                    organized_units[building][floor].append(unit)
    
    # Debug information
    print(f"Total tenants: {len(tenants)}")
    print(f"Total units: {len(units)}")
    for building in buildings:
        for floor in floors:
            print(f"Building {building}, Floor {floor}: {len(organized_units[building][floor])} units")
    
    return render_template('admin/manage_tenants.html',
                         tenants=tenants,
                         units=units,
                         buildings=buildings,
                         floors=floors,
                         organized_units=organized_units)

@views.route('/admin/payment/<int:payment_id>/details')
@login_required
def payment_details(payment_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        payment = Payment.query\
            .join(User, Payment.tenant_id == User.id)\
            .filter(Payment.id == payment_id)\
            .first_or_404()
        
        return jsonify({
            'tenant_name': f"{payment.tenant.first_name} {payment.tenant.last_name}",
            'unit_number': payment.tenant.unit_number or 'No Unit',
            'amount': format_currency(payment.amount),
            'payment_date': payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else None,
            'due_date': payment.due_date.strftime('%Y-%m-%d') if payment.due_date else None,
            'status': payment.status,
            'payment_method': payment.payment_method or 'Not specified',
            'reference_number': payment.reference_number,
            'proof_of_payment': payment.proof_of_payment,
            'created_date': payment.created_date.strftime('%Y-%m-%d')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@views.route('/admin/payment/<int:payment_id>/approve', methods=['POST'])
@login_required
def approve_payment(payment_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        payment = Payment.query.get_or_404(payment_id)
        if payment.status == 'paid':
            return jsonify({'error': 'Payment already approved'}), 400
            
        payment.status = 'paid'
        payment.payment_date = datetime.utcnow()
        
        # Create notification for tenant
        notification = Notification(
            user_id=payment.tenant_id,
            message=f"Your payment of {format_currency(payment.amount)} has been approved.",
            type='payment'
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@views.route('/admin/notices')
@login_required
def notices():
    if current_user.user_type != 'admin':
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))
        
    notices = Notice.query.order_by(Notice.created_date.desc()).all()
    tenants = User.query.filter_by(user_type='tenant').order_by(User.first_name).all()
    
    # Get counts for different notice types
    stats = {
        'payment': Notice.query.filter_by(type='payment').count(),
        'maintenance': Notice.query.filter_by(type='maintenance').count(),
        'announcement': Notice.query.filter_by(type='announcement').count(),
        'urgent': Notice.query.filter_by(type='urgent').count()
    }
    
    return render_template('admin/notices.html', notices=notices, stats=stats, tenants=tenants)

@views.route('/admin/notices/create', methods=['POST'])
@login_required
def create_notice():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    try:
        data = request.json
        recipient_type = data.get('recipient_type')
        recipients = data.get('recipients', [])

        # If specific tenants selected, use their IDs
        if recipient_type == 'specific_tenants':
            recipient_list = recipients
        else:
            # For other types, store the type itself
            recipient_list = [recipient_type]
        
        notice = Notice(
            title=data.get('title'),
            message=data.get('message'),
            type=data.get('type'),
            recipients=','.join(recipient_list),
            notification_methods=json.dumps(data.get('notification_methods')),
            created_by=current_user.id,
            scheduled_date=datetime.fromisoformat(data.get('schedule_datetime')) 
                if data.get('schedule') == 'schedule' else None
        )
        
        db.session.add(notice)
        db.session.commit()
        
        # Send immediate notifications if not scheduled
        if data.get('schedule') == 'send_now':
            send_notifications(notice)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@views.route('/admin/notices/<int:notice_id>/delete', methods=['DELETE'])
@login_required
def delete_notice(notice_id):
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    notice = Notice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()
    
    return jsonify({'success': True})

def send_notifications(notice):
    """Helper function to send notifications via different methods"""
    methods = json.loads(notice.notification_methods)
    recipients = notice.recipients.split(',')
    
    if methods.get('email'):
        # Send email notifications
        pass
        
    if methods.get('sms'):
        # Send SMS notifications
        pass
        
    if methods.get('push'):
        # Send push notifications
        pass
        
    notice.status = 'sent'
    notice.sent_date = datetime.utcnow()
    db.session.commit()

@views.route('/admin/reports')
@login_required
def reports():
    if current_user.user_type != 'admin':
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))
    
    # Get basic statistics
    total_revenue = db.session.query(func.sum(Payment.amount))\
        .filter(Payment.status == 'paid').scalar() or 0
        
    total_expected = db.session.query(func.sum(Unit.rent_amount))\
        .filter(Unit.status == 'occupied').scalar() or 0
        
    collection_rate = (total_revenue / total_expected * 100) if total_expected > 0 else 0
    
    # Calculate outstanding balance
    outstanding_balance = db.session.query(func.sum(User.balance))\
        .filter(User.user_type == 'tenant')\
        .scalar() or 0
    
    occupied_units = Unit.query.filter_by(status='occupied').count()
    total_units = Unit.query.count()
    occupancy_rate = (occupied_units / total_units * 100) if total_units > 0 else 0
    
    # Get revenue trend data (last 6 months)
    months = []
    revenue_data = []
    for i in range(5, -1, -1):
        date = datetime.now() - timedelta(days=i*30)
        months.append(date.strftime('%B %Y'))
        month_revenue = db.session.query(func.sum(Payment.amount))\
            .filter(Payment.status == 'paid')\
            .filter(extract('month', Payment.payment_date) == date.month)\
            .filter(extract('year', Payment.payment_date) == date.year)\
            .scalar() or 0
        revenue_data.append(float(month_revenue))
    
    # Get payment distribution
    payment_distribution = [
        Payment.query.filter_by(status='paid').count(),
        Payment.query.filter_by(status='pending').count(),
        Payment.query.filter_by(status='overdue').count()
    ]
    
    # Get units with related data
    units = Unit.query\
        .outerjoin(User, Unit.current_tenant_id == User.id)\
        .outerjoin(Payment, User.id == Payment.tenant_id)\
        .with_entities(
            Unit,
            func.count(Payment.id).label('payment_count'),
            func.sum(case((Payment.status == 'paid', Payment.amount), else_=0)).label('total_paid')
        )\
        .group_by(Unit.id)\
        .all()
    
    return render_template(
        'admin/reports.html',
        total_revenue=total_revenue,
        outstanding_balance=outstanding_balance,
        collection_rate=round(collection_rate, 1),
        occupancy_rate=round(occupancy_rate, 1),
        revenue_labels=months,
        revenue_data=revenue_data,
        payment_distribution=payment_distribution,
        units=units
    )

@views.route('/admin/reports/data', methods=['POST'])
@login_required
def get_report_data():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.json
    report_type = data.get('report_type')
    start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d')
    end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d')
    
    if report_type == 'financial':
        return get_financial_report(start_date, end_date)
    elif report_type == 'occupancy':
        return get_occupancy_report(start_date, end_date)
    elif report_type == 'maintenance':
        return get_maintenance_report(start_date, end_date)
    elif report_type == 'tenant':
        return get_tenant_report(start_date, end_date)
    
    return jsonify({'error': 'Invalid report type'})

def get_financial_report(start_date, end_date):
    # Implement financial report logic
    pass

def get_occupancy_report(start_date, end_date):
    # Implement occupancy report logic
    pass

def get_maintenance_report(start_date, end_date):
    # Implement maintenance report logic
    pass

def get_tenant_report(start_date, end_date):
    # Implement tenant report logic
    pass

@views.route('/admin/settings')
@login_required
def settings():
    if current_user.user_type != 'admin':
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))
        
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
        
    return render_template('admin/settings.html', settings=settings)

@views.route('/admin/settings/profile', methods=['POST'])
@login_required
def update_profile_settings():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    try:
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.email = request.form.get('email')
        current_user.phone = request.form.get('phone')
        
        new_password = request.form.get('new_password')
        if new_password:
            current_user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@views.route('/admin/settings/system', methods=['POST'])
@login_required
def update_system_settings():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    try:
        settings = Settings.query.first()
        settings.property_name = request.form.get('property_name')
        settings.business_address = request.form.get('business_address')
        settings.contact_email = request.form.get('contact_email')
        settings.contact_phone = request.form.get('contact_phone')
        settings.currency_symbol = request.form.get('currency_symbol')
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@views.route('/admin/settings/notifications', methods=['POST'])
@login_required
def update_notification_settings():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    try:
        settings = Settings.query.first()
        settings.payment_reminder_email = 'payment_reminder_email' in request.form
        settings.payment_reminder_sms = 'payment_reminder_sms' in request.form
        settings.reminder_days = int(request.form.get('reminder_days', 5))
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@views.route('/admin/settings/payments', methods=['POST'])
@login_required
def update_payment_settings():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    try:
        settings = Settings.query.first()
        settings.late_payment_fee = float(request.form.get('late_payment_fee', 0))
        settings.grace_period = int(request.form.get('grace_period', 3))
        settings.accept_cash = 'accept_cash' in request.form
        settings.accept_bank_transfer = 'accept_bank_transfer' in request.form
        settings.accept_gcash = 'accept_gcash' in request.form
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@views.route('/admin/settings/backup', methods=['POST'])
@login_required
def backup_database():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    try:
        # Implement database backup logic here
        settings = Settings.query.first()
        settings.last_backup_date = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@views.route('/tenant/unit-dashboard')
@login_required
def unit_dashboard():
    if current_user.user_type != 'tenant':
        return redirect(url_for('admin.dashboard'))
    
    # Get current tenant's unit with full details
    unit = Unit.query.filter_by(current_tenant_id=current_user.id).first()
    
    # Get last payment
    last_payment = Payment.query.filter_by(
        tenant_id=current_user.id,
        status='paid'
    ).order_by(Payment.payment_date.desc()).first()
    
    # Get maintenance history for the unit
    maintenance_history = MaintenanceRequest.query.filter_by(
        unit_id=unit.id if unit else None
    ).order_by(MaintenanceRequest.created_date.desc()).limit(5).all()
    
    # Get available units (excluding current tenant's unit)
    available_units = Unit.query.filter(
        Unit.status.in_(['vacant', 'maintenance']),
        Unit.id != (unit.id if unit else None)
    ).all()
    
    return render_template('tenant/unit_dashboard.html',
                         unit=unit,
                         last_payment=last_payment,
                         maintenance_history=maintenance_history,
                         available_units=available_units)

@views.route('/tenant/express-interest', methods=['POST'])
@login_required
def express_interest():
    if current_user.user_type != 'tenant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.json
    admin = User.query.filter_by(user_type='admin').first()
    
    # Create notification for admin
    notification = Notification(
        user_id=admin.id,
        message=f"Unit Interest: Tenant {current_user.first_name} (Unit {current_user.unit_number}) is interested in Unit {data.get('unit_number')}. Message: {data.get('message')}",
        type='unit_interest'
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({'success': True})

@views.route('/admin/unit/<string:unit_number>/details')
@login_required
def unit_details(unit_number):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    unit = Unit.query.filter_by(unit_number=unit_number).first_or_404()
    
    return jsonify({
        'unit_number': unit.unit_number,
        'status': unit.status,
        'floor': unit.floor,
        'building': unit.building,
        'rent_amount': format_currency(unit.rent_amount),
        'tenant': {
            'name': f"{unit.tenant.first_name} {unit.tenant.last_name}" if unit.tenant else None,
            'phone': unit.tenant.phone if unit.tenant else None,
            'move_in_date': unit.tenant.created_date.strftime('%Y-%m-%d') if unit.tenant else None
        } if unit.tenant else None
    })

@views.route('/admin/payments')
@login_required
def admin_payments():
    if current_user.user_type != 'admin':
        flash('Access denied. Admin access only.', 'error')
        return redirect(url_for('views.home'))
    
    try:
        # Get all payments with tenant information
        all_payments = Payment.query\
            .join(User, Payment.tenant_id == User.id)\
            .order_by(Payment.created_date.desc())\
            .all()
        
        # Get pending payments
        pending_payments = [p for p in all_payments if p.status == 'pending']
        
        # Get overdue payments
        overdue_payments = [p for p in all_payments 
                          if p.due_date and p.due_date < datetime.utcnow() 
                          and p.status != 'paid']
        
        # Calculate monthly collections
        current_month = datetime.utcnow().replace(day=1)
        monthly_collections = 0.0
        for payment in all_payments:
            if (payment.status == 'paid' and 
                payment.payment_date and 
                payment.payment_date >= current_month):
                monthly_collections += float(payment.amount)

        # Calculate collection rate
        current_month = datetime.utcnow().month
        total_due = 0.0
        total_collected = 0.0
        for payment in all_payments:
            if payment.due_date and payment.due_date.month == current_month:
                total_due += float(payment.amount)
            if (payment.status == 'paid' and 
                payment.payment_date and 
                payment.payment_date.month == current_month):
                total_collected += float(payment.amount)

        collection_rate = round((total_collected / total_due * 100)) if total_due > 0 else 0
        
        # Get payment trends
        payment_months = []
        payment_trends = []
        for i in range(5, -1, -1):
            date = datetime.utcnow() - timedelta(days=30*i)
            start_date = date.replace(day=1)
            end_date = (date.replace(day=1) + timedelta(days=32)).replace(day=1) if i > 0 else datetime.utcnow()
            
            month_total = 0.0
            for payment in all_payments:
                if (payment.status == 'paid' and 
                    payment.payment_date and 
                    start_date <= payment.payment_date < end_date):
                    month_total += float(payment.amount)
            
            payment_months.append(date.strftime('%B'))
            payment_trends.append(month_total)

        print("Debug - Collections:", monthly_collections)  # Add debug prints
        print("Debug - Rate:", collection_rate)
        print("Debug - Trends:", payment_trends)
        
        return render_template('admin/payment_dashboard.html',
                             all_payments=all_payments,
                             pending_payments=pending_payments,
                             overdue_payments=overdue_payments,
                             monthly_collections=monthly_collections,
                             collection_rate=collection_rate,
                             payment_months=payment_months,
                             payment_trends=payment_trends)
                             
    except Exception as e:
        print(f"Payment dashboard error: {str(e)}")  # Add debug print
        import traceback
        print(traceback.format_exc())  # Print full error traceback
        flash(f'Error loading payment dashboard: {str(e)}', category='error')
        return redirect(url_for('views.home'))

@views.route('/admin/create-user', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.user_type != 'admin':
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))
    
    try:
        if request.method == 'GET':
            # Get available units and convert to dictionaries
            available_units = Unit.query.filter_by(status='vacant').order_by(Unit.unit_number).all()
            units_data = [{
                'unit_number': unit.unit_number,
                'floor': unit.floor,
                'building': unit.building,
                'rent_amount': float(unit.rent_amount)  # Convert Decimal to float for JSON
            } for unit in available_units]
            
            return render_template('admin/create_user.html', available_units=units_data)
        
        if request.method == 'POST':
            email = request.form.get('email')
            password1 = request.form.get('password1')
            password2 = request.form.get('password2')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            phone = request.form.get('phone')
            address = request.form.get('address')
            emergency_contact_name = request.form.get('emergency_contact_name')
            emergency_contact_phone = request.form.get('emergency_contact_phone')
            user_type = request.form.get('user_type')
            unit_number = request.form.get('unit_number') if user_type == 'tenant' else None
            
            # Validation checks
            if password1 != password2:
                flash('Passwords don\'t match', category='error')
                return redirect(url_for('views.create_user'))
                
            if User.query.filter_by(email=email).first():
                flash('Email already registered', category='error')
                return redirect(url_for('views.create_user'))
            
            # Check if unit is available (for tenants)
            if user_type == 'tenant' and unit_number:
                unit = Unit.query.filter_by(unit_number=unit_number, status='vacant').first()
                if not unit:
                    flash('Selected unit is no longer available', category='error')
                    return redirect(url_for('views.create_user'))
            
            # Create new user
            new_user = User(
                email=email,
                password=generate_password_hash(password1, method='pbkdf2:sha256'),
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                address=address,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                unit_number=unit_number,
                user_type=user_type
            )
            
            db.session.add(new_user)
            
            # Update unit status if tenant
            if user_type == 'tenant' and unit_number:
                unit = Unit.query.filter_by(unit_number=unit_number).first()
                if unit:
                    unit.status = 'occupied'
                    unit.current_tenant_id = new_user.id
            
            db.session.commit()
            
            flash(f'User account created successfully!', category='success')
            if user_type == 'tenant':
                return redirect(url_for('views.manage_tenants'))
            return redirect(url_for('admin.dashboard'))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', category='error')
        return redirect(url_for('views.create_user'))

@views.route('/admin/notices/<int:notice_id>/details')
@login_required
def get_notice_details(notice_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    notice = Notice.query.get_or_404(notice_id)
    
    return jsonify({
        'id': notice.id,
        'type': notice.type,
        'title': notice.title,
        'message': notice.message,
        'recipients': notice.recipients,
        'notification_methods': notice.notification_methods,
        'status': notice.status,
        'created_date': notice.created_date.strftime('%Y-%m-%d %H:%M'),
        'scheduled_date': notice.scheduled_date.strftime('%Y-%m-%d %H:%M') if notice.scheduled_date else None,
        'sent_date': notice.sent_date.strftime('%Y-%m-%d %H:%M') if notice.sent_date else None
    })

@views.route('/admin/notices/<int:notice_id>/update', methods=['POST'])
@login_required
def update_notice(notice_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        notice = Notice.query.get_or_404(notice_id)
        data = request.json
        
        notice.type = data.get('type', notice.type)
        notice.title = data.get('title', notice.title)
        notice.message = data.get('message', notice.message)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@views.route('/admin/maintenance')
@login_required
def admin_maintenance():
    if current_user.user_type != 'admin':
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))
    
    try:
        # Get all maintenance requests
        maintenance_requests = MaintenanceRequest.query\
            .join(Unit, MaintenanceRequest.unit_id == Unit.id)\
            .join(User, Unit.current_tenant_id == User.id)\
            .order_by(MaintenanceRequest.created_date.desc())\
            .all()
            
        # Get statistics
        stats = {
            'total': MaintenanceRequest.query.count(),
            'pending': MaintenanceRequest.query.filter_by(status='pending').count(),
            'in_progress': MaintenanceRequest.query.filter_by(status='in_progress').count(),
            'completed': MaintenanceRequest.query.filter_by(status='completed').count()
        }
        
        return render_template(
            'admin/maintenance.html',
            maintenance_requests=maintenance_requests,
            stats=stats
        )
        
    except Exception as e:
        flash(f'Error loading maintenance dashboard: {str(e)}', category='error')
        return redirect(url_for('views.home'))

@views.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.user_type != 'admin':
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))
    
    try:
        # Get basic statistics
        total_revenue = db.session.query(func.sum(Payment.amount))\
            .filter(Payment.status == 'paid').scalar() or 0
            
        # Calculate monthly revenue
        current_month = datetime.utcnow().replace(day=1)
        monthly_revenue = db.session.query(func.sum(Payment.amount))\
            .filter(Payment.status == 'paid')\
            .filter(Payment.payment_date >= current_month)\
            .scalar() or 0
            
        # Get occupancy statistics
        total_units = Unit.query.count()
        occupied_units = Unit.query.filter_by(status='occupied').count()
        occupancy_rate = (occupied_units / total_units * 100) if total_units > 0 else 0
        
        # Get maintenance statistics
        maintenance_requests = MaintenanceRequest.query.count()
        pending_maintenance = MaintenanceRequest.query.filter_by(status='pending').count()
        
        # Get tenant statistics
        total_tenants = User.query.filter_by(user_type='tenant').count()
        
        stats = {
            'total_revenue': float(total_revenue),
            'monthly_revenue': float(monthly_revenue),
            'total_units': total_units,
            'occupied_units': occupied_units,
            'occupancy_rate': round(occupancy_rate, 1),
            'maintenance_requests': maintenance_requests,
            'pending_maintenance': pending_maintenance,
            'total_tenants': total_tenants,
            'vacant_units': total_units - occupied_units,
            'maintenance_units': pending_maintenance
        }
        
        # Get recent activities
        recent_payments = Payment.query\
            .join(User, Payment.tenant_id == User.id)\
            .order_by(Payment.created_date.desc())\
            .limit(5).all()
            
        recent_maintenance = MaintenanceRequest.query\
            .join(Unit, MaintenanceRequest.unit_id == Unit.id)\
            .order_by(MaintenanceRequest.created_date.desc())\
            .limit(5).all()
        
        return render_template(
            'admin/dashboard.html',  # This is the main dashboard template
            stats=stats,
            recent_payments=recent_payments,
            recent_maintenance=recent_maintenance
        )
        
    except Exception as e:
        flash(f'Dashboard error: {str(e)}', category='error')
        return redirect(url_for('views.home'))

@views.route('/admin/complaints')
@login_required
def admin_complaints():
    if current_user.user_type != 'admin':
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))
        
    complaints = Complaint.query\
        .join(User, Complaint.tenant_id == User.id)\
        .order_by(Complaint.created_date.desc()).all()
        
    stats = {
        'total': Complaint.query.count(),
        'pending': Complaint.query.filter_by(status='pending').count(),
        'in_progress': Complaint.query.filter_by(status='in_progress').count(),
        'resolved': Complaint.query.filter_by(status='resolved').count()
    }
    
    return render_template('admin/complaints.html', complaints=complaints, stats=stats)

@views.route('/admin/complaints/<int:complaint_id>/reply', methods=['POST'])
@login_required
def admin_reply_complaint(complaint_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        complaint = Complaint.query.get_or_404(complaint_id)
        data = request.json
        
        complaint.admin_reply = data.get('reply')
        complaint.status = data.get('status', 'in_progress')
        if data.get('status') == 'resolved':
            complaint.resolved_date = datetime.utcnow()
            
        # Create notification for tenant
        notification = Notification(
            user_id=complaint.tenant_id,
            title='Complaint Update',
            message=f'Your complaint "{complaint.subject}" has been {complaint.status}',
            type='complaint_update'
        )
        db.session.add(notification)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@views.before_request
def before_request():
    if current_user.is_authenticated and current_user.user_type == 'admin':
        # Get pending complaints count for the sidebar badge
        g.complaint_stats = {
            'pending': Complaint.query.filter_by(status='pending').count()
        }
    