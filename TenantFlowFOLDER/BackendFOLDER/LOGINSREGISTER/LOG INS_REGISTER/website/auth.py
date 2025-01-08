from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, limiter  # Import limiter from __init__.py
from flask_login import login_user, login_required, logout_user, current_user
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables

# You can set this in your .env file or define it here
ADMIN_CODE = 'ADMIN_CODE'

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if not user.can_login():
                flash('This account has been deactivated.', category='error')
            elif user.check_password(password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template("login.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=['GET', 'POST'])
@limiter.limit("5 per hour")  # Limit sign-ups
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        admin_code = request.form.get('admin_code')
        
        role = 'tenant'  # Default role
        if admin_code == ADMIN_CODE:  # Check against the defined admin code
            role = 'admin'

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            new_user = User(
                email=email,
                first_name=first_name,
                role=role
            )
            new_user.set_password(password1)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)


@auth.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    user = current_user
    logout_user()
    user.delete_user()
    flash('Your account has been deleted.', category='success')
    return redirect(url_for('auth.login'))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Access denied. Admin privileges required.', category='error')
            return redirect(url_for('views.home'))
        return f(*args, **kwargs)
    return decorated_function