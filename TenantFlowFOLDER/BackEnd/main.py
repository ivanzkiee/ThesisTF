from website import create_app
from flask_migrate import Migrate
from website.extensions import db

app = create_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    try:
        app.run(debug=True, port=5000, host='127.0.0.1')
    except Exception as e:
        print(f"Error starting the application: {str(e)}")
        exit(1) 