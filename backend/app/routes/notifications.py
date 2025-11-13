from flask import Blueprint, request, jsonify
from app.models.notification import Notification
from app.routes.auth import verify_token
from app import mongo
from bson import ObjectId

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/notifications', methods=['GET', 'OPTIONS'])
def get_notifications():
    """Get user's notifications"""
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
        notification_model = Notification(mongo.db)
        
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 20))
        
        notifications = notification_model.get_user_notifications(
            user_id, 
            limit=limit, 
            unread_only=unread_only
        )
        
        unread_count = notification_model.get_unread_count(user_id)
        
        return jsonify({
            'notifications': notifications,
            'unread_count': unread_count
        }), 200
        
    except Exception as e:
        print(f"❌ Error fetching notifications: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch notifications'}), 500


@notifications_bp.route('/notifications/<notification_id>/read', methods=['POST', 'OPTIONS'])
def mark_notification_read(notification_id):
    """Mark a notification as read"""
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
        notification_model = Notification(mongo.db)
        notification_model.mark_as_read(notification_id)
        
        return jsonify({'message': 'Notification marked as read'}), 200
    except Exception as e:
        print(f"❌ Error marking notification as read: {str(e)}")
        return jsonify({'error': 'Failed to mark as read'}), 500


@notifications_bp.route('/notifications/read-all', methods=['POST', 'OPTIONS'])
def mark_all_read():
    """Mark all notifications as read"""
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
        notification_model = Notification(mongo.db)
        notification_model.mark_all_as_read(user_id)
        
        return jsonify({'message': 'All notifications marked as read'}), 200
    except Exception as e:
        print(f"❌ Error marking all as read: {str(e)}")
        return jsonify({'error': 'Failed to mark all as read'}), 500


@notifications_bp.route('/notifications/<notification_id>', methods=['DELETE', 'OPTIONS'])
def delete_notification(notification_id):
    """Delete a notification"""
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
        notification_model = Notification(mongo.db)
        notification_model.delete(notification_id)
        
        return jsonify({'message': 'Notification deleted'}), 200
    except Exception as e:
        print(f"❌ Error deleting notification: {str(e)}")
        return jsonify({'error': 'Failed to delete notification'}), 500
