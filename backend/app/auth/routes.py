from flask import Blueprint, request, jsonify
from app import db
from app.models import User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validate required fields - check for None, empty string, or missing
    email = data.get('email') if data else None
    password = data.get('password') if data else None
    name = data.get('name') if data else None
    
    if not email or not isinstance(email, str) or not email.strip():
        return jsonify({'error': 'Email is required'}), 400
    if not password or not isinstance(password, str) or len(password.strip()) < 6:
        return jsonify({'error': 'Password is required and must be at least 6 characters'}), 400
    if not name or not isinstance(name, str) or not name.strip():
        return jsonify({'error': 'Name is required'}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=email.strip().lower()).first():
        return jsonify({'error': 'User with this email already exists'}), 400
    
    user = User(
        email=email.strip().lower(),
        password_hash=generate_password_hash(password),
        name=name.strip(),
        phone=data.get('phone', '').strip() if data.get('phone') else None
    )
    
    db.session.add(user)
    db.session.commit()
    
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'User created successfully',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'phone': user.phone
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing email or password'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'phone': user.phone
        }
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'phone': user.phone,
        'created_at': user.created_at.isoformat()
    }), 200

@auth_bp.route('/update-fcm-token', methods=['POST'])
@jwt_required()
def update_fcm_token():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    user.fcm_token = data.get('fcm_token')
    user.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'message': 'FCM token updated successfully'}), 200
