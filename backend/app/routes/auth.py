from flask import Blueprint, request, jsonify, send_from_directory, current_app
from datetime import datetime, timedelta, timezone
import jwt
from app.models import User
from app import mongo
import os
from bson import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


auth_bp = Blueprint('auth', __name__)
user_model = User(mongo.db)


# Secret key for JWT (should be in environment variables)
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this')


# Avatar upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def get_upload_folder():
    """Get upload folder from app config or use default"""
    try:
        return current_app.config.get('UPLOAD_FOLDER', 'uploads/avatars')
    except:
        return 'uploads/avatars'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_token(user_id):
    """Generate JWT token with UTC timezone"""
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'exp': now + timedelta(days=7),
        'iat': now
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token


def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        print(f"✅ Token verified for user: {payload['user_id']}")
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        print("❌ Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"❌ Invalid token: {e}")
        return None
    except Exception as e:
        print(f"❌ Token verification error: {e}")
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
        
        user = user_model.create(name, email, password)
        
        if not user:
            return jsonify({'error': 'User with this email already exists'}), 409
        
        token = generate_token(user['_id'])
        print(f"✅ New user registered: {email}, token generated")
        
        return jsonify({
            'message': 'Registration successful',
            'token': token,
            'user': user
        }), 201
        
    except Exception as e:
        print(f"❌ Registration error: {e}")
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
        
        user = user_model.authenticate(email, password)
        
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        token = generate_token(user['_id'])
        print(f"✅ User logged in: {email}, token generated")
        print(f"🖼️ Avatar: {user.get('avatar')}")  # Debug log
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user  # This should include avatar
        }), 200
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/me', methods=['GET', 'OPTIONS'])
def get_current_user():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        print("❌ No token in Authorization header")
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    user = user_model.get_by_id(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user}), 200

@auth_bp.route('/upload-avatar', methods=['POST', 'OPTIONS'])
def upload_avatar():
    """Upload user avatar"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    if 'avatar' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['avatar']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': 'File size exceeds 5MB limit'}), 400
    
    if file and allowed_file(file.filename):
        UPLOAD_FOLDER = get_upload_folder()
        
        # Delete old avatar if exists
        user = user_model.collection.find_one({'_id': ObjectId(user_id)})
        if user and user.get('avatar'):
            # Extract filename from URL
            old_filename = user.get('avatar').split('/')[-1]
            old_avatar_path = os.path.join(UPLOAD_FOLDER, old_filename)
            if os.path.exists(old_avatar_path):
                try:
                    os.remove(old_avatar_path)
                    print(f"✅ Deleted old avatar: {old_filename}")
                except Exception as e:
                    print(f"❌ Error deleting old avatar: {e}")
        
        # Create unique filename
        timestamp = int(datetime.now(timezone.utc).timestamp())
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"{user_id}_{timestamp}.{file_extension}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save file
        file.save(filepath)
        print(f"✅ Avatar saved: {filepath}")
        print(f"📂 File exists: {os.path.exists(filepath)}")
        
        # Return full URL (but DON'T update database yet - let update_profile do it)
        avatar_url = f"http://localhost:5000/uploads/avatars/{filename}"
        
        print(f"✅ Avatar URL generated: {avatar_url}")
        return jsonify({'avatar_url': avatar_url}), 200
    
    return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400

@auth_bp.route('/profile', methods=['PUT', 'OPTIONS'])
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
        print(f"📥 Received update data: {data}")  # Debug
        
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'email' in data:
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
        if 'avatar' in data and data['avatar']:  # ✅ Ensure avatar is not empty
            update_data['avatar'] = data['avatar']
            print(f"✅ Updating avatar to: {data['avatar']}")  # Debug
        
        print(f"💾 Updating database with: {update_data}")  # Debug
        
        user_model.collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        
        user = user_model.get_by_id(user_id)
        print(f"✅ Updated user avatar: {user.get('avatar')}")  # Debug
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user
        }), 200
        
    except Exception as e:
        print(f"Error updating profile: {str(e)}")
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
        
        user = user_model.collection.find_one({'_id': ObjectId(user_id)})
        
        if not user or not check_password_hash(user['password_hash'], current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
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
        current_user = mongo.db.users.find_one({'_id': ObjectId(current_user_id)})
        friends_list = current_user.get('friends', [])
        
        if user_id == current_user_id or user_id in friends_list:
            essays = list(mongo.db.essays.find({'user_id': user_id}))
        else:
            public_posts = list(mongo.db.posts.find({
                'author_id': user_id,
                'visibility': 'public'
            }))
            essay_ids = [post.get('essay_id') for post in public_posts]
            essays = list(mongo.db.essays.find({'_id': {'$in': [ObjectId(eid) for eid in essay_ids]}}))
        
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
    
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
            return response, 200
        
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            print("❌ No token in Authorization header")
            return jsonify({'error': 'No token provided'}), 401
        
        token = auth_header.split(' ')[1]
        user_id = verify_token(token)
        
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        user = user_model.get_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        print(f"✅ Returning user data with avatar: {user.get('avatar')}")  # Debug log
        return jsonify({'user': user}), 200

