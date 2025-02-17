from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from ...models import Unit, User
from ... import db
from datetime import datetime

unit_management = Blueprint('unit_management', __name__)

@unit_management.route('/admin/units')
@login_required
def manage_units():
    if current_user.user_type != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('views.home'))
        
    units = Unit.query.all()
    return render_template('admin/units/manage_units.html', units=units)

@unit_management.route('/admin/unit/<string:unit_number>', methods=['GET', 'POST'])
@login_required
def unit_details(unit_number):
    if current_user.user_type != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('views.home'))
        
    unit = Unit.query.filter_by(unit_number=unit_number).first_or_404()
    
    if request.method == 'POST':
        unit.status = request.form.get('status')
        unit.rent_amount = float(request.form.get('rent_amount'))
        unit.floor = int(request.form.get('floor'))
        unit.building = request.form.get('building')
        
        if unit.status == 'maintenance':
            unit.last_maintenance_date = datetime.utcnow()
            
        db.session.commit()
        flash('Unit updated successfully!', 'success')
        
    return render_template('admin/units/unit_details.html', unit=unit)

@unit_management.route('/admin/unit/add', methods=['GET', 'POST'])
@login_required
def add_unit():
    if current_user.user_type != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('views.home'))
        
    if request.method == 'POST':
        new_unit = Unit(
            unit_number=request.form.get('unit_number'),
            status='vacant',
            floor=int(request.form.get('floor')),
            building=request.form.get('building'),
            rent_amount=float(request.form.get('rent_amount'))
        )
        db.session.add(new_unit)
        db.session.commit()
        flash('Unit added successfully!', 'success')
        return redirect(url_for('unit_management.manage_units'))
        
    return render_template('admin/units/add_unit.html')

@unit_management.route('/api/units/status')
def get_units_status():
    units = Unit.query.all()
    status_count = {
        'total': len(units),
        'occupied': sum(1 for u in units if u.status == 'occupied'),
        'vacant': sum(1 for u in units if u.status == 'vacant'),
        'maintenance': sum(1 for u in units if u.status == 'maintenance')
    }
    return jsonify(status_count) 