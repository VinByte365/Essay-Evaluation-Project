from flask import Blueprint, request, jsonify
from app.models import Post, Essay
from app.routes.auth import verify_token
from app import mongo
from bson import ObjectId

posts_bp = Blueprint('posts', __name__)
post_model = Post(mongo.db)
essay_model = Essay(mongo.db)

@posts_bp.route('/posts', methods=['GET', 'OPTIONS'])
def get_posts():
    """Get feed posts"""
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
    
    posts = post_model.get_feed(user_id)
    return jsonify({'posts': posts}), 200

@posts_bp.route('/posts', methods=['POST', 'OPTIONS'])
def create_post():
    """Create a new post (share essay)"""
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
        essay_id = data.get('essay_id')
        caption = data.get('caption', '')
        visibility = data.get('visibility', 'public')
        
        # Get essay details
        essay = essay_model.get_by_id(essay_id)
        if not essay:
            return jsonify({'error': 'Essay not found'}), 404
        
        # Get user details (from token)
        from app.models import User
        user_model = User(mongo.db)
        user = user_model.get_by_id(user_id)
        
        # Create post
        post = post_model.create(
            author_id=user_id,
            author_name=user['name'],
            author_email=user['email'],
            essay_id=essay_id,
            essay_title=essay['title'],
            essay_score=essay.get('score', 0),
            caption=caption,
            visibility=visibility
        )
        
        return jsonify({'post': post}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@posts_bp.route('/posts/<post_id>/like', methods=['POST', 'OPTIONS'])
def like_post(post_id):
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
        post_model.like_post(post_id)
        return jsonify({'message': 'Post liked'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@posts_bp.route('/posts/<post_id>/comment', methods=['POST', 'OPTIONS'])
def comment_post(post_id):
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
        from app.models import User
        user_model = User(mongo.db)
        user = user_model.get_by_id(user_id)
        
        data = request.get_json()
        comment_text = data.get('comment')
        
        post_model.add_comment(post_id, user_id, user['name'], comment_text)
        return jsonify({'message': 'Comment added'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
