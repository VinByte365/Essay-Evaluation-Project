from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import jwt
from app.models import User
from app import mongo
import os
from bson import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash



auth_bp = Blueprint('auth', __name__)
user_model = User(mongo.db)

# Secret key for JWT (should be in environment variables)
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this')

def generate_token(user_id):
    """Generate JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7),  # Token expires in 7 days
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@auth_bp.route('/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        if not all([name, email, password]):
            return jsonify({'error': 'All fields are required'}), 400
        
        # Create user
        user = user_model.create(name, email, password)
        
        if not user:
            return jsonify({'error': 'User with this email already exists'}), 409
        
        # Generate JWT token
        token = generate_token(user['_id'])
        
        return jsonify({
            'message': 'Registration successful',
            'token': token,
            'user': user
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not all([email, password]):
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Authenticate user
        user = user_model.authenticate(email, password)
        
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Generate JWT token
        token = generate_token(user['_id'])
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/me', methods=['GET', 'OPTIONS'])
def get_current_user():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    user = user_model.get_by_id(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user}), 200

@auth_bp.route('/profile', methods=['PUT', 'OPTIONS'])  # ← Remove /auth/ 
def update_profile():
    """Update user profile information"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT, OPTIONS')
        return response, 200
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    try:
        data = request.get_json()
        
        # Update user in database
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'email' in data:
            # Check if email is already taken by another user
            existing = user_model.collection.find_one({
                'email': data['email'],
                '_id': {'$ne': ObjectId(user_id)}
            })
            if existing:
                return jsonify({'error': 'Email already in use'}), 409
            update_data['email'] = data['email']
        if 'location' in data:
            update_data['location'] = data['location']
        if 'bio' in data:
            update_data['bio'] = data['bio']
        
        user_model.collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        
        # Get updated user
        user = user_model.get_by_id(user_id)
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user
        }), 200
        
    except Exception as e:
        print(f"Error updating profile: {str(e)}")  # ← Add logging
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST', 'OPTIONS'])
def change_password():
    """Change user password"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Both passwords required'}), 400
        
        # Get user with password hash
        user = user_model.collection.find_one({'_id': ObjectId(user_id)})
        
        if not user or not check_password_hash(user['password_hash'], current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        new_hash = generate_password_hash(new_password)
        user_model.collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'password_hash': new_hash}}
        )
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        print(f"Error changing password: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/users/<user_id>/stats', methods=['GET', 'OPTIONS'])
def get_user_stats(user_id):
    """Get user's public statistics"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    current_user_id = verify_token(token)
    
    if not current_user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    try:
        # Get user's public or friends-visible essays based on friendship status
        current_user = mongo.db.users.find_one({'_id': ObjectId(current_user_id)})
        friends_list = current_user.get('friends', [])
        
        # Determine if current user can view this user's stats
        if user_id == current_user_id or user_id in friends_list:
            # Can view full stats
            essays = list(mongo.db.essays.find({'user_id': user_id}))
        else:
            # Can only view public essays (essays that are shared publicly)
            public_posts = list(mongo.db.posts.find({
                'author_id': user_id,
                'visibility': 'public'
            }))
            essay_ids = [post.get('essay_id') for post in public_posts]
            essays = list(mongo.db.essays.find({'_id': {'$in': [ObjectId(eid) for eid in essay_ids]}}))
        
        # Calculate stats
        completed = [e for e in essays if e.get('status') == 'completed']
        scores = [e.get('score', 0) for e in completed if e.get('score', 0) > 0]
        
        avg_score = round(sum(scores) / len(scores)) if scores else 0
        high_score = max(scores) if scores else 0
        
        return jsonify({
            'total_essays': len(essays),
            'completed_essays': len(completed),
            'average_score': avg_score,
            'highest_score': high_score
        }), 200
        
    except Exception as e:
        print(f"Error fetching user stats: {str(e)}")
        return jsonify({'error': str(e)}), 500
