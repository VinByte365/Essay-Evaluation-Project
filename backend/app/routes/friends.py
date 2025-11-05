from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from app.models import User
from app.routes.auth import verify_token
from app import mongo
from bson import ObjectId


friends_bp = Blueprint('friends', __name__)
user_model = User(mongo.db)


@friends_bp.route('/friends/request', methods=['POST', 'OPTIONS'])
def send_friend_request():
    """Send friend request"""
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
    
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    
    if not receiver_id:
        return jsonify({'error': 'Receiver ID required'}), 400
    
    if user_id == receiver_id:
        return jsonify({'error': 'Cannot send friend request to yourself'}), 400
    
    try:
        # Call the User model method (which has the debug prints)
        result = user_model.send_friend_request(user_id, receiver_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"❌ Error sending friend request: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@friends_bp.route('/friends/status/<user_id>', methods=['GET', 'OPTIONS'])
def check_friendship_status(user_id):
    """Check friendship status with a user"""
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
        print(f"🔍 Checking friendship status: current_user={current_user_id}, target_user={user_id}")
        
        # Check if already friends
        current_user = mongo.db.users.find_one({'_id': ObjectId(current_user_id)})
        if user_id in current_user.get('friends', []):
            print(f"✅ Already friends")
            return jsonify({'status': 'friends'}), 200
        
        # Check if current user SENT a request (they should see "pending")
        sent_request = mongo.db.friend_requests.find_one({
            'from_user_id': current_user_id,
            'to_user_id': user_id,
            'status': 'pending'
        })
        
        if sent_request:
            print(f"📤 Current user sent a pending request")
            return jsonify({'status': 'pending'}), 200
        
        # Check if current user RECEIVED a request (they should see "received")
        received_request = mongo.db.friend_requests.find_one({
            'from_user_id': user_id,
            'to_user_id': current_user_id,
            'status': 'pending'
        })
        
        if received_request:
            print(f"📥 Current user received a pending request")
            return jsonify({'status': 'received'}), 200
        
        # No relationship
        print(f"✅ No relationship")
        return jsonify({'status': 'none'}), 200
    
    except Exception as e:
        print(f"❌ Error checking friendship status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@friends_bp.route('/friends/requests/pending', methods=['GET', 'OPTIONS'])
def get_pending_requests():
    """Get pending friend requests"""
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
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    print(f"🔍 Fetching pending requests for user: {user_id}")
    requests = user_model.get_pending_requests(user_id)
    print(f"📊 Returning {len(requests)} requests")
    return jsonify({'requests': requests}), 200

@friends_bp.route('/friends/request/<request_id>/accept', methods=['POST', 'OPTIONS'])
def accept_request(request_id):
    """Accept friend request"""
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
    
    result = user_model.accept_friend_request(request_id, user_id)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result), 200

@friends_bp.route('/friends/request/<request_id>/reject', methods=['POST', 'OPTIONS'])
def reject_request(request_id):
    """Reject friend request"""
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
    
    result = user_model.reject_friend_request(request_id, user_id)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result), 200

@friends_bp.route('/friends/request/cancel/<receiver_id>', methods=['POST', 'OPTIONS'])
def cancel_friend_request(receiver_id):
    """Cancel a sent friend request"""
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
        print(f"🔴 Cancelling request: from={user_id}, to={receiver_id}")
        
        # Find and delete using from_user_id/to_user_id
        result = mongo.db.friend_requests.delete_one({
            'from_user_id': user_id,
            'to_user_id': receiver_id,
            'status': 'pending'
        })
        
        if result.deleted_count > 0:
            print(f"✅ Friend request cancelled")
            return jsonify({'message': 'Friend request cancelled'}), 200
        else:
            print(f"⚠️ No pending request found")
            return jsonify({'error': 'No pending request found'}), 404
            
    except Exception as e:
        print(f"❌ Error cancelling friend request: {str(e)}")
        return jsonify({'error': str(e)}), 500

@friends_bp.route('/friends/suggestions', methods=['GET', 'OPTIONS'])
def get_suggestions():
    """Get friend suggestions"""
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
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    suggestions = user_model.get_friend_suggestions(user_id)
    return jsonify({'suggestions': suggestions}), 200

@friends_bp.route('/friends', methods=['GET', 'OPTIONS'])
def get_friends():
    """Get user's friends list"""
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
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    try:
        # Get user's friends list
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        friend_ids = user.get('friends', [])
        
        # Get friend details
        friends = []
        for friend_id in friend_ids:
            friend = mongo.db.users.find_one({'_id': ObjectId(friend_id)})
            if friend:
                friends.append({
                    'id': str(friend['_id']),
                    'name': friend.get('name', 'Unknown'),
                    'email': friend.get('email', ''),
                    'location': friend.get('location'),
                    'bio': friend.get('bio')
                })
        
        return jsonify({'friends': friends}), 200
        
    except Exception as e:
        print(f"Error fetching friends: {str(e)}")
        return jsonify({'error': str(e)}), 500

@friends_bp.route('/friends/<friend_id>', methods=['DELETE', 'OPTIONS'])
def remove_friend(friend_id):
    """Remove a friend"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE, OPTIONS')
        return response, 200
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    try:
        # Remove from both users' friends lists
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$pull': {'friends': friend_id}}
        )
        
        mongo.db.users.update_one(
            {'_id': ObjectId(friend_id)},
            {'$pull': {'friends': user_id}}
        )
        
        # Mark any existing friend requests as cancelled (using from_user_id/to_user_id)
        mongo.db.friend_requests.update_many(
            {
                '$or': [
                    {'from_user_id': user_id, 'to_user_id': friend_id},
                    {'from_user_id': friend_id, 'to_user_id': user_id}
                ]
            },
            {'$set': {
                'status': 'cancelled',
                'updated_at': datetime.now(timezone.utc)
            }}
        )
        
        print(f"✅ Friend removed: {user_id} ✗ {friend_id}")
        return jsonify({'message': 'Friend removed'}), 200
        
    except Exception as e:
        print(f"❌ Error removing friend: {str(e)}")
        return jsonify({'error': str(e)}), 500
