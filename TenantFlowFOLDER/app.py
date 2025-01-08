from flask import Flask, request, jsonify, render_template
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import User

def create_app():
    # Initialize Flask app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('config.Config')
    
    # Initialize extensions
    db.init_app(app)
    
    # Error handling helper
    def handle_error(message, status_code=400):
        return jsonify({"error": message}), status_code

    # Routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/users', methods=['GET'])
    def get_users():
        try:
            users = User.query.all()
            return jsonify([user.to_dict() for user in users])
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/users', methods=['POST'])
    def create_user():
        try:
            data = request.get_json()
            
            # Validate input
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            username = data.get('username')
            email = data.get('email')
            
            if not username or not email:
                return jsonify({"error": "Username and email are required"}), 400
            
            # Create new user
            new_user = User(username=username, email=email)
            db.session.add(new_user)
            db.session.commit()
            
            return jsonify({
                "message": "User created successfully",
                "user": new_user.to_dict()
            }), 201
            
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "Email already exists"}), 409
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/users/<int:id>', methods=['GET'])
    def get_user(id):
        user = User.query.get(id)
        if not user:
            return handle_error("User not found.", 404)
        return jsonify(user.to_dict())

    @app.route('/users/<int:id>', methods=['PUT'])
    def update_user(id):
        user = User.query.get(id)
        if not user:
            return handle_error("User not found.", 404)
        
        data = request.json
        if data.get('username'):
            user.username = data['username']
        if data.get('email'):
            user.email = data['email']

        try:
            db.session.commit()
            return jsonify({"message": "User updated!", "user": user.to_dict()})
        except IntegrityError:
            db.session.rollback()
            return handle_error("Email must be unique.", 409)

    @app.route('/users/<int:id>', methods=['DELETE'])
    def delete_user(id):
        try:
            user = User.query.get(id)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            db.session.delete(user)
            db.session.commit()
            return jsonify({"message": "User deleted successfully"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    return app