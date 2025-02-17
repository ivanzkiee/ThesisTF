from website import create_app, db
from website.models import User, Unit
from werkzeug.security import generate_password_hash
import os

def init_database():
    app = create_app()
    
    with app.app_context():
        # Create instance directory if it doesn't exist
        if not os.path.exists('instance'):
            os.makedirs('instance')
            print("Created instance directory")

        # Create uploads directories
        uploads_paths = [
            'website/static/uploads',
            'website/static/uploads/payments',
            'website/static/uploads/maintenance'
        ]
        for path in uploads_paths:
            if not os.path.exists(path):
                os.makedirs(path)
                print(f"Created {path} directory")

        # Initialize database
        db.drop_all()
        db.create_all()
        
        # Create admin user
        admin = User(
            email='admin@example.com',
            password=generate_password_hash('Admin123!', method='pbkdf2:sha256'),
            first_name='Admin',
            last_name='User',
            phone='09123456789',
            address='Main Office',
            emergency_contact_name='Emergency Contact',
            emergency_contact_phone='09123456789',
            user_type='admin'
        )
        
        # Create test tenant
        tenant = User(
            email='tenant@example.com',
            password=generate_password_hash('Tenant123!', method='pbkdf2:sha256'),
            first_name='John',
            last_name='Doe',
            phone='09123456789',
            address='123 Main St',
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='09123456789',
            user_type='tenant',
            unit_number='101'
        )
        
        db.session.add(admin)
        db.session.add(tenant)
        db.session.commit()
        
        # Add sample units (5 buildings, 5 floors each, 7 units per floor)
        buildings = ['A', 'B', 'C', 'D', 'E']
        floors = 5
        units_per_floor = 7

        for building in buildings:
            for floor in range(1, floors + 1):
                for unit in range(1, units_per_floor + 1):
                    # Format: building + floor + unit (e.g., A101, B102, etc.)
                    unit_number = f"{building}{floor}0{unit}"
                    sample_unit = Unit(
                        unit_number=unit_number,
                        status='vacant',  # Default status
                        floor=floor,
                        building=f'Building {building}',
                        rent_amount=15000 + (floor * 1000) + (buildings.index(building) * 2000),  # Rent varies by floor and building
                    )
                    db.session.add(sample_unit)

        db.session.commit()
        
        # Update the first tenant's unit
        tenant = User.query.filter_by(email='tenant@example.com').first()
        if tenant:
            unit = Unit.query.filter_by(unit_number='A101').first()
            if unit:
                unit.status = 'occupied'
                unit.current_tenant_id = tenant.id
                tenant.unit_number = 'A101'
                db.session.commit()
        
        print('Database initialized!')
        print('\nTest Accounts:')
        print('Admin - Email: admin@example.com, Password: Admin123!')
        print('Tenant - Email: tenant@example.com, Password: Tenant123!')

if __name__ == '__main__':
    init_database() 