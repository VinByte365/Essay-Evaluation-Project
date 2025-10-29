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
    """Get all posts (feed)"""
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
        
        # Get posts (public + friends-only from friends)
        posts = list(mongo.db.posts.find({
            '$or': [
                {'visibility': 'public'},
                {'author_id': {'$in': friends_list}, 'visibility': 'friends'},
                {'author_id': user_id}  # Include own posts
            ]
        }).sort('shared_at', -1))
        
        # Populate author details and essay info
        result = []
        for post in posts:
            # Get author info including avatar
            author = mongo.db.users.find_one({'_id': ObjectId(post['author_id'])})
            
            # Get essay info
            essay = mongo.db.essays.find_one({'_id': ObjectId(post['essay_id'])})
            
            if author and essay:
                # Convert likes array to count
                likes = post.get('likes', [])
                likes_count = len(likes) if isinstance(likes, list) else likes
                
                # Convert comments array to count
                comments = post.get('comments', [])
                comments_count = len(comments) if isinstance(comments, list) else comments
                
                # ✅ NEW: Get essay content preview (first 300 characters)
                essay_content = essay.get('content', '')
                content_preview = essay_content[:300] if essay_content else None
                
                result.append({
                    'id': str(post['_id']),
                    'author_id': post['author_id'],
                    'author_name': author.get('name', 'Unknown'),
                    'author_email': author.get('email', ''),
                    'author_avatar': author.get('avatar'),
                    'essay_id': post['essay_id'],
                    'essay_title': essay.get('title', 'Untitled'),
                    'essay_score': essay.get('score', 0),
                    'essay_content': content_preview,  # ✅ Add content preview
                    'caption': post.get('caption', ''),
                    'shared_at': post.get('shared_at').isoformat() if hasattr(post.get('shared_at'), 'isoformat') else str(post.get('shared_at')),
                    'visibility': post.get('visibility', 'public'),
                    'likes': likes_count,
                    'comments': comments_count,
                    'shares': post.get('shares', 0)
                })
        
        return jsonify({'posts': result}), 200
        
    except Exception as e:
        print(f"Error fetching posts: {str(e)}")
        import traceback
        traceback.print_exc()
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
        
        # Create post with arrays
        post = {
            'author_id': user_id,
            'author_name': user.get('name', 'Unknown'),
            'author_email': user.get('email', ''),
            'essay_id': essay_id,
            'essay_title': essay.get('title', 'Untitled'),
            'essay_score': essay.get('score', 0),
            'caption': caption,
            'visibility': visibility,
            'shared_at': datetime.now(),
            'likes': [],  # Array of user IDs
            'comments': [],  # Array of comment objects
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
    """Toggle like on a post (like/unlike)"""
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
        # Get the post to check if user has already liked
        post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        likes = post.get('likes', [])
        
        # Toggle like: if user already liked, remove; otherwise add
        if user_id in likes:
            # Unlike
            result = mongo.db.posts.update_one(
                {'_id': ObjectId(post_id)},
                {'$pull': {'likes': user_id}}
            )
            return jsonify({'message': 'Post unliked', 'liked': False}), 200
        else:
            # Like
            result = mongo.db.posts.update_one(
                {'_id': ObjectId(post_id)},
                {'$addToSet': {'likes': user_id}}
            )
            return jsonify({'message': 'Post liked', 'liked': True}), 200
            
    except Exception as e:
        print(f"Error toggling like: {str(e)}")
        return jsonify({'error': str(e)}), 500


@posts_bp.route('/posts/<post_id>/check-like', methods=['GET', 'OPTIONS'])
def check_like_status(post_id):
    """Check if current user has liked a post"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Authorization')
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
        post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        likes = post.get('likes', [])
        liked = user_id in likes
        
        return jsonify({'liked': liked}), 200
        
    except Exception as e:
        print(f"Error checking like status: {str(e)}")
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
        post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        comments = post.get('comments', [])
        
        # Populate user details for each comment including avatar
        populated_comments = []
        for comment in comments:
            user = mongo.db.users.find_one({'_id': ObjectId(comment['user_id'])})
            if user:
                populated_comments.append({
                    'user_id': comment['user_id'],
                    'user_name': user.get('name', 'Unknown'),
                    'user_avatar': user.get('avatar'),
                    'text': comment['text'],
                    'created_at': comment['created_at']
                })
        
        return jsonify({'comments': populated_comments}), 200
        
    except Exception as e:
        print(f"Error fetching comments: {str(e)}")
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
