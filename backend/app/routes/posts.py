from flask import Blueprint, request, jsonify
from app.models import Post, Essay
from app.routes.auth import verify_token
from app import mongo
from bson import ObjectId
from datetime import datetime

posts_bp = Blueprint('posts', __name__)
post_model = Post(mongo.db)
essay_model = Essay(mongo.db)

@posts_bp.route('/posts', methods=['GET', 'OPTIONS'])
def get_posts():
    """Get posts for feed (public + friends' posts)"""
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
        # Get current user's friends list
        current_user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        friends_list = current_user.get('friends', [])
        
        # Fetch posts that are either:
        # 1. Public posts
        # 2. Friends-only posts from friends
        # 3. User's own posts (any visibility)
        posts = list(mongo.db.posts.find({
            '$or': [
                {'visibility': 'public'},  # All public posts
                {'author_id': user_id},  # User's own posts
                {
                    'visibility': 'friends',  # Friends-only posts
                    'author_id': {'$in': friends_list}  # From friends
                }
            ]
        }).sort('shared_at', -1))
        
        # Format posts for response
        formatted_posts = []
        for post in posts:
            formatted_post = {
                'id': str(post['_id']),
                'author_id': post['author_id'],
                'author_name': post['author_name'],
                'author_email': post['author_email'],
                'essay_id': post['essay_id'],
                'essay_title': post['essay_title'],
                'essay_score': post.get('essay_score', 0),
                'caption': post.get('caption', ''),
                'visibility': post['visibility'],
                'shared_at': post['shared_at'].isoformat(),
                'likes': len(post.get('likes', [])),
                'comments': post.get('comments', []),
                'shares': post.get('shares', 0)
            }
            formatted_posts.append(formatted_post)
        
        return jsonify({'posts': formatted_posts}), 200
        
    except Exception as e:
        print(f"Error fetching posts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@posts_bp.route('/posts', methods=['POST', 'OPTIONS'])
def create_post():
    """Share an essay as a post"""
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
    essay_id = data.get('essay_id')
    caption = data.get('caption', '')
    visibility = data.get('visibility', 'public')
    
    if not essay_id:
        return jsonify({'error': 'Essay ID required'}), 400
    
    try:
        # Get essay details
        essay = mongo.db.essays.find_one({'_id': ObjectId(essay_id)})
        if not essay:
            return jsonify({'error': 'Essay not found'}), 404
        
        # Get user details
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        # ✅ UPDATED: Create post with arrays
        post = {
            'author_id': user_id,
            'author_name': user.get('name', 'Unknown'),
            'author_email': user.get('email', ''),
            'essay_id': essay_id,
            'essay_title': essay.get('title', 'Untitled'),
            'essay_score': essay.get('score', 0),
            'caption': caption,
            'visibility': visibility,
            'shared_at': datetime.utcnow(),
            'likes': [],  # ✅ Array of user IDs
            'comments': [],  # ✅ Array of comment objects
            'shares': 0  # Number
        }
        
        result = mongo.db.posts.insert_one(post)
        
        return jsonify({
            'message': 'Post created',
            'post_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        print(f"Error creating post: {str(e)}")
        return jsonify({'error': str(e)}), 500

@posts_bp.route('/posts/<post_id>/like', methods=['POST', 'OPTIONS'])
def like_post(post_id):
    """Like a post"""
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
        # ✅ UPDATED: Add user_id to likes array (prevents duplicates)
        result = mongo.db.posts.update_one(
            {'_id': ObjectId(post_id)},
            {'$addToSet': {'likes': user_id}}  # $addToSet prevents duplicates
        )
        
        if result.modified_count > 0:
            return jsonify({'message': 'Post liked'}), 200
        else:
            return jsonify({'message': 'Already liked or post not found'}), 200
            
    except Exception as e:
        print(f"Error liking post: {str(e)}")
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

@posts_bp.route('/posts/<post_id>/comments', methods=['GET', 'OPTIONS'])
def get_comments(post_id):
    """Get comments for a post"""
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
        # ✅ Get post and return comments array
        post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        comments = post.get('comments', [])
        
        return jsonify({'comments': comments}), 200
        
    except Exception as e:
        print(f"Error fetching comments: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    """Get current user's posts"""
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
        # Get user's posts
        posts = list(mongo.db.posts.find({'author_id': user_id}).sort('shared_at', -1))
        
        # Format posts
        formatted_posts = []
        for post in posts:
            # Handle likes
            likes = post.get('likes', [])
            likes_count = len(likes) if isinstance(likes, list) else likes
            
            # Handle comments
            comments = post.get('comments', [])
            comment_count = len(comments) if isinstance(comments, list) else comments
            
            formatted_posts.append({
                'id': str(post['_id']),
                'essay_id': post.get('essay_id'),
                'essay_title': post.get('essay_title'),
                'caption': post.get('caption'),
                'visibility': post.get('visibility'),
                'shared_at': post.get('shared_at').isoformat() if hasattr(post.get('shared_at'), 'isoformat') else str(post.get('shared_at')),
                'likes': likes_count,
                'comments': comment_count,
                'shares': post.get('shares', 0)
            })
        
        return jsonify({'posts': formatted_posts}), 200
        
    except Exception as e:
        print(f"Error fetching user posts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@posts_bp.route('/posts/my-posts', methods=['GET', 'OPTIONS'])
def get_my_posts():
    """Get current user's posts"""
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
        # Get user's posts
        posts = list(mongo.db.posts.find({'author_id': user_id}).sort('shared_at', -1))
        
        # Format posts
        formatted_posts = []
        for post in posts:
            # Handle likes
            likes = post.get('likes', [])
            likes_count = len(likes) if isinstance(likes, list) else likes
            
            # Handle comments
            comments = post.get('comments', [])
            comment_count = len(comments) if isinstance(comments, list) else comments
            
            formatted_posts.append({
                'id': str(post['_id']),
                'essay_id': post.get('essay_id'),
                'essay_title': post.get('essay_title'),
                'caption': post.get('caption'),
                'visibility': post.get('visibility'),
                'shared_at': post.get('shared_at').isoformat() if hasattr(post.get('shared_at'), 'isoformat') else str(post.get('shared_at')),
                'likes': likes_count,
                'comments': comment_count,
                'shares': post.get('shares', 0)
            })
        
        return jsonify({'posts': formatted_posts}), 200
        
    except Exception as e:
        print(f"Error fetching user posts: {str(e)}")
        return jsonify({'error': str(e)}), 500
