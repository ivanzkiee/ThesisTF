from flask import Blueprint, render_template, request, flash, jsonify, current_app, redirect, url_for, send_file, abort
from flask_login import login_required, current_user
from .models import Note, Payment, User, Notification
from . import db
import json
import os
from werkzeug.utils import secure_filename
import pdfkit  # Install with: pip install pdfkit
import io
from datetime import datetime, timedelta
from .auth import admin_required
import csv
from sqlalchemy.sql import func, extract
from sqlalchemy import extract, func

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST': 
        note = request.form.get('note')#Gets the note from the HTML 

        if len(note) < 1:
            flash('Note is too short!', category='error') 
        else:
            new_note = Note(data=note, user_id=current_user.id)  #providing the schema for the note 
            db.session.add(new_note) #adding the note to the database 
            db.session.commit()
            flash('Note added!', category='success')

    return render_template("home.html", user=current_user)


@views.route('/delete-note', methods=['POST'])
def delete_note():  
    note = json.loads(request.data) # this function expects a JSON from the INDEX.js file 
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()

    return jsonify({})


@views.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            # Update user information
            current_user.first_name = request.form.get('first_name')
            current_user.phone = request.form.get('phone')
            current_user.unit_number = request.form.get('unit_number')
            
            # Handle profile picture upload
            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                if file and file.filename:
                    # Create profile_pics directory if it doesn't exist
                    profile_pics_dir = os.path.join(current_app.root_path, 'static/profile_pics')
                    os.makedirs(profile_pics_dir, exist_ok=True)
                    
                    # Save the file
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(profile_pics_dir, filename)
                    file.save(file_path)
                    current_user.profile_pic = f'/static/profile_pics/{filename}'
            
            db.session.commit()
            flash('Profile updated successfully!', category='success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', category='error')
            print(f"Error: {str(e)}")  # For debugging
            
        return redirect(url_for('views.profile'))

    return render_template("profile.html", user=current_user)


@views.route('/payments', methods=['GET', 'POST'])
@login_required
def payments():
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            method = request.form.get('method')
            reference = request.form.get('reference')

            payment = Payment(
                amount=amount,
                method=method,
                reference=reference,
                user_id=current_user.id,
                status='pending'
            )
            db.session.add(payment)
            db.session.commit()

            # Generate reference number after getting ID
            payment.reference = payment.generate_reference()
            db.session.commit()

            # Send notification
            send_payment_notification(payment)

            flash('Payment submitted successfully!', category='success')
            return redirect(url_for('views.payments'))
        except Exception as e:
            flash(f'Error submitting payment: {str(e)}', category='error')

    # Get current year
    current_year = datetime.now().year

    # Get payment statistics
    stats = {
        'total_paid': current_user.get_total_paid(current_year),
        'next_due': current_user.get_next_payment_due(),
        'outstanding': current_user.get_outstanding_balance()
    }

    payments = Payment.query.filter_by(user_id=current_user.id)\
        .order_by(Payment.date.desc()).all()

    return render_template(
        "payments.html",
        user=current_user,
        payments=payments,
        stats=stats,
        now=datetime.now()
    )

@views.route('/generate-receipt/<int:payment_id>')
@login_required
def generate_receipt(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    if payment.user_id != current_user.id:
        abort(403)

    # Generate HTML for the receipt
    receipt_html = render_template(
        'receipt.html',
        payment=payment,
        user=current_user
    )

    # Convert HTML to PDF
    pdf = pdfkit.from_string(receipt_html, False)

    # Create response
    response = send_file(
        io.BytesIO(pdf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'receipt_{payment.reference}.pdf'
    )

    return response

def send_payment_notification(payment):
    # You can implement email/SMS notification here
    print(f"Payment notification for {payment.reference}")

@views.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    users = User.query.filter_by(role='tenant').all()
    total_payments = Payment.query.count()
    pending_payments = Payment.query.filter_by(status='pending').count()
    
    return render_template(
        'admin/dashboard.html',
        user=current_user,
        tenants=users,
        total_payments=total_payments,
        pending_payments=pending_payments
    )

@views.route('/admin/tenants')
@login_required
@admin_required
def manage_tenants():
    try:
        # Only get users with role='tenant'
        tenants = User.query.filter_by(role='tenant').all()
        current_app.logger.info(f"Found {len(tenants)} tenants")
        return render_template('admin/tenants.html', tenants=tenants, user=current_user)
    except Exception as e:
        current_app.logger.error(f"Error in manage_tenants: {str(e)}")
        flash('Error loading tenants', category='error')
        return redirect(url_for('views.home'))

@views.route('/admin/payments')
@login_required
@admin_required
def manage_payments():
    try:
        # Get all payments
        payments = Payment.query.order_by(Payment.date.desc()).all()
        
        # Get all tenants for the modals
        tenants = User.query.filter_by(role='tenant').all()
        
        # Calculate statistics
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Total collections this month
        total_collections = db.session.query(func.sum(Payment.amount))\
            .filter(Payment.status == 'paid')\
            .filter(extract('month', Payment.date) == current_month)\
            .filter(extract('year', Payment.date) == current_year)\
            .scalar() or 0
        
        # Get pending payments
        pending_payments = Payment.query.filter_by(status='pending').all()
        
        # Get overdue payments (assuming payment is overdue after 5 days)
        five_days_ago = datetime.now() - timedelta(days=5)
        overdue_payments = Payment.query.filter(
            Payment.status == 'pending',
            Payment.date < five_days_ago
        ).all()
        
        # Count paid tenants this month
        paid_tenants = db.session.query(Payment.user_id)\
            .filter(Payment.status == 'paid')\
            .filter(extract('month', Payment.date) == current_month)\
            .filter(extract('year', Payment.date) == current_year)\
            .distinct().count()
        
        total_tenants = User.query.filter_by(role='tenant').count()

        return render_template(
            'admin/payments.html',
            payments=payments,
            tenants=tenants,
            total_collections=total_collections,
            pending_payments=pending_payments,
            overdue_payments=overdue_payments,
            paid_tenants=paid_tenants,
            total_tenants=total_tenants,
            user=current_user
        )
    except Exception as e:
        current_app.logger.error(f"Error in manage_payments: {str(e)}")
        flash('Error loading payments dashboard', category='error')
        return redirect(url_for('views.home'))

@views.route('/admin/tenant/<int:tenant_id>')
@login_required
@admin_required
def manage_tenant(tenant_id):
    try:
        tenant = User.query.get_or_404(tenant_id)
        if not tenant.is_tenant():
            abort(404)
        return render_template('admin/manage_tenant.html', tenant=tenant)
    except Exception as e:
        current_app.logger.error(f'Error in manage_tenant: {str(e)}')
        raise

@views.route('/admin/approve-payment/<int:payment_id>', methods=['POST'])
@login_required
@admin_required
def approve_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    payment.status = 'paid'
    db.session.commit()
    flash('Payment approved successfully!', category='success')
    return redirect(url_for('views.manage_payments'))

@views.route('/admin/update-tenant/<int:tenant_id>', methods=['POST'])
@login_required
@admin_required
def update_tenant(tenant_id):
    tenant = User.query.get_or_404(tenant_id)
    if not tenant.is_tenant():
        abort(404)
    
    tenant.unit_number = request.form.get('unit_number')
    lease_start = request.form.get('lease_start')
    if lease_start:
        tenant.lease_start = datetime.strptime(lease_start, '%Y-%m-%d')
    
    db.session.commit()
    flash('Tenant details updated successfully!', category='success')
    return redirect(url_for('views.manage_tenant', tenant_id=tenant_id))

@views.route('/admin/add-payment/<int:tenant_id>', methods=['POST'])
@login_required
@admin_required
def add_payment(tenant_id):
    tenant = User.query.get_or_404(tenant_id)
    if not tenant.is_tenant():
        abort(404)
    
    try:
        amount = float(request.form.get('amount'))
        method = request.form.get('method')
        notes = request.form.get('notes')

        payment = Payment(
            amount=amount,
            method=method,
            notes=notes,
            user_id=tenant.id,
            status='pending'
        )
        db.session.add(payment)
        db.session.commit()

        # Generate reference number after getting ID
        payment.reference = payment.generate_reference()
        db.session.commit()

        flash('Payment added successfully!', category='success')
    except Exception as e:
        flash(f'Error adding payment: {str(e)}', category='error')
    
    return redirect(url_for('views.manage_tenant', tenant_id=tenant_id))

@views.route('/admin/activate-tenant/<int:tenant_id>', methods=['POST'])
@login_required
@admin_required
def activate_tenant(tenant_id):
    tenant = User.query.get_or_404(tenant_id)
    if not tenant.is_tenant():
        abort(404)
    
    tenant.is_active = True
    db.session.commit()
    flash('Tenant account activated successfully!', category='success')
    return redirect(url_for('views.manage_tenant', tenant_id=tenant_id))

@views.route('/admin/deactivate-tenant/<int:tenant_id>', methods=['POST'])
@login_required
@admin_required
def deactivate_tenant(tenant_id):
    tenant = User.query.get_or_404(tenant_id)
    if not tenant.is_tenant():
        abort(404)
    
    tenant.is_active = False
    db.session.commit()
    flash('Tenant account deactivated successfully!', category='success')
    return redirect(url_for('views.manage_tenant', tenant_id=tenant_id))

@views.route('/admin/add-tenant-note', methods=['POST'])
@login_required
@admin_required
def add_tenant_note():
    try:
        tenant_id = request.form.get('tenant_id')
        note_text = request.form.get('note')
        
        tenant = User.query.get_or_404(tenant_id)
        note = Note(data=note_text, user_id=tenant.id)
        
        db.session.add(note)
        db.session.commit()
        
        flash('Note added successfully!', category='success')
    except Exception as e:
        flash('Error adding note', category='error')
        current_app.logger.error(f"Error adding note: {str(e)}")
    
    return redirect(url_for('views.manage_tenants'))

@views.route('/admin/tenant-notes/<int:tenant_id>')
@login_required
@admin_required
def get_tenant_notes(tenant_id):
    tenant = User.query.get_or_404(tenant_id)
    notes = [{'data': note.data, 'date': note.date.strftime('%Y-%m-%d %H:%M')} 
             for note in tenant.notes]
    return jsonify(notes)

@views.route('/admin/send-payment-reminder', methods=['POST'])
@login_required
@admin_required
def send_payment_reminder():
    tenant_ids = request.form.getlist('tenant_ids[]')
    message = request.form.get('message')
    
    for tenant_id in tenant_ids:
        tenant = User.query.get(tenant_id)
        if tenant:
            # Create notification for tenant
            notification = Notification(
                user_id=tenant.id,
                title='Payment Reminder',
                message=message,
                type='payment_reminder'
            )
            db.session.add(notification)
    
    db.session.commit()
    flash('Payment reminders sent successfully!', category='success')
    return redirect(url_for('views.manage_payments'))

@views.route('/admin/generate-soa', methods=['POST'])
@login_required
@admin_required
def generate_soa():
    tenant_id = request.form.get('tenant_id')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    tenant = User.query.get_or_404(tenant_id)
    
    # Generate SOA HTML
    soa_html = render_template(
        'admin/soa_template.html',
        tenant=tenant,
        start_date=start_date,
        end_date=end_date,
        payments=tenant.payments
    )
    
    # Convert to PDF
    pdf = pdfkit.from_string(soa_html, False)
    
    # Create response
    response = send_file(
        io.BytesIO(pdf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'SOA_{tenant.first_name}_{start_date}_{end_date}.pdf'
    )
    
    return response

@views.route('/admin/export-payments')
@login_required
@admin_required
def export_payments():
    # Create CSV of payments
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Date', 'Tenant', 'Unit', 'Amount', 'Status', 'Reference'])
    
    # Write payment data
    payments = Payment.query.all()
    for payment in payments:
        writer.writerow([
            payment.date.strftime('%Y-%m-%d'),
            payment.user.first_name,
            payment.user.unit_number,
            payment.amount,
            payment.status,
            payment.reference
        ])
    
    # Create response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='payments_export.csv'
    )

@views.route('/notifications')
@login_required
def notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.date_created.desc()).all()
    return render_template('notifications.html', notifications=notifications, user=current_user)

@views.route('/mark-notification-read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
    return jsonify({'success': True})