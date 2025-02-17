from setuptools import setup, find_packages

setup(
    name="tenantflow",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "flask>=2.0.0",
        "Flask-SQLAlchemy>=2.5.1",
        "Flask-Login>=0.5.0",
        "Flask-WTF>=0.15.1",
        "Werkzeug>=2.0.1",
        "python-dateutil>=2.8.1",
        "MarkupSafe>=2.0.1",
        "Jinja2>=3.0.1",
        "SQLAlchemy>=1.4.23",
        "WTForms>=2.3.3",
        "python-dotenv>=0.19.0",
        "Pillow>=9.0.0",  # For image handling
        "qrcode>=7.0",    # For QR code generation
    ],
    python_requires=">=3.8",
) 