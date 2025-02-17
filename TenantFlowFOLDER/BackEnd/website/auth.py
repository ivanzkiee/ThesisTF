from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User, Unit
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.user_type == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('views.tenant_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            
            if user.user_type == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('views.tenant_dashboard'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        # Get available units and convert to dictionaries
        available_units = Unit.query.filter_by(status='vacant').order_by(Unit.unit_number).all()
        units_data = [{
            'unit_number': unit.unit_number,
            'floor': unit.floor,
            'building': unit.building,
            'rent_amount': float(unit.rent_amount)  # Convert Decimal to float for JSON
        } for unit in available_units]
        
        return render_template('auth/register.html', available_units=units_data)
    
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
        unit_number = request.form.get('unit_number')
        
        # Validation checks
        if password1 != password2:
            flash('Passwords don\'t match', category='error')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered', category='error')
            return redirect(url_for('auth.register'))
        
        # Check if unit is available
        unit = Unit.query.filter_by(unit_number=unit_number, status='vacant').first()
        if not unit:
            flash('Selected unit is no longer available', category='error')
            return redirect(url_for('auth.register'))
        
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
            user_type='tenant'
        )
        
        # Update unit status
        unit.status = 'occupied'
        unit.current_tenant_id = new_user.id
        
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user, remember=True)
        flash('Account created successfully!', category='success')
        return redirect(url_for('views.tenant_dashboard'))