import os
import shutil
from website import create_app, db
from website.models import User, Unit
from werkzeug.security import generate_password_hash
from datetime import datetime

def reset_database():
    print("Starting database reset...")
    
    # Delete existing database file
    db_path = os.path.join('instance', 'database.db')
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("Deleted existing database")
        except Exception as e:
            print(f"Error deleting database: {e}")
            return

    # Create instance directory if it doesn't exist
    if not os.path.exists('instance'):
        os.makedirs('instance')
        print("Created instance directory")

    # Create/recreate uploads directories
    uploads_path = os.path.join('website', 'static', 'uploads')
    if os.path.exists(uploads_path):
        shutil.rmtree(uploads_path)
    os.makedirs(os.path.join(uploads_path, 'payments'), exist_ok=True)
    os.makedirs(os.path.join(uploads_path, 'maintenance'), exist_ok=True)
    print("Created upload directories")

    # Initialize app and create database
    app = create_app()
    with app.app_context():
        print("Creating database tables...")
        db.create_all()

        try:
            # Create admin user
            admin = User(
                email='admin@example.com',
                first_name='Admin',
                last_name='Administrator',
                password=generate_password_hash('Admin123!', method='sha256'),
                user_type='admin',
                phone='09123456789',
                address='Agustin and Son Realty Office',
                emergency_contact_name='System Administrator',
                emergency_contact_phone='09123456789'
            )
            db.session.add(admin)

            # Create test tenants
            tenants = [
                {
                    'email': 'tenant1@example.com',
                    'password': 'Tenant123!',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'phone': '09123456789',
                    'address': '123 Main Street, Manila',
                    'emergency_contact_name': 'Jane Doe',
                    'emergency_contact_phone': '09187654321',
                    'unit_number': '101'
                },
                {
                    'email': 'tenant2@example.com',
                    'password': 'Tenant123!',
                    'first_name': 'Maria',
                    'last_name': 'Santos',
                    'phone': '09234567890',
                    'address': '456 Park Avenue, Makati',
                    'emergency_contact_name': 'Juan Santos',
                    'emergency_contact_phone': '09198765432',
                    'unit_number': '102'
                }
            ]

            # Create units first
            for unit_number in ['101', '102']:
                unit = Unit(
                    unit_number=unit_number,
                    status='occupied',
                    floor=int(unit_number[0]),
                    building='Building A',
                    rent_amount=10000.00
                )
                db.session.add(unit)
            
            db.session.commit()

            # Create tenant accounts
            for tenant_data in tenants:
                tenant = User(
                    email=tenant_data['email'],
                    password=generate_password_hash(tenant_data['password'], method='sha256'),
                    first_name=tenant_data['first_name'],
                    last_name=tenant_data['last_name'],
                    phone=tenant_data['phone'],
                    address=tenant_data['address'],
                    emergency_contact_name=tenant_data['emergency_contact_name'],
                    emergency_contact_phone=tenant_data['emergency_contact_phone'],
                    user_type='tenant',
                    unit_number=tenant_data['unit_number']
                )
                db.session.add(tenant)

            db.session.commit()
            print("\nAccounts created successfully!")
            print("\nAdmin Account:")
            print("Email: admin@example.com")
            print("Password: Admin123!")
            print("\nTenant Accounts:")
            print("1. Email: tenant1@example.com")
            print("   Password: Tenant123!")
            print("   Unit: 101")
            print("\n2. Email: tenant2@example.com")
            print("   Password: Tenant123!")
            print("   Unit: 102")

        except Exception as e:
            db.session.rollback()
            print(f"Error creating accounts: {e}")
            return

if __name__ == "__main__":
    reset_database()
    print("\nDatabase reset completed!") 