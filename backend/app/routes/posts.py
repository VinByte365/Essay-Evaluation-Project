from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
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
        current_user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        friends_list = current_user.get('friends', [])
        
        posts = list(mongo.db.posts.find({
            '$or': [
                {'visibility': 'public'},
                {'author_id': {'$in': friends_list}, 'visibility': 'friends'},
                {'author_id': user_id}
            ]
        }).sort('shared_at', -1))
        
        result = []
        for post in posts:
            author = mongo.db.users.find_one({'_id': ObjectId(post['author_id'])})
            essay = mongo.db.essays.find_one({'_id': ObjectId(post['essay_id'])})
            
            # ✅ NEW: If this is a shared post, fetch original author
            original_author = None
            if post.get('is_share') and post.get('original_author_id'):
                original_author = mongo.db.users.find_one({'_id': ObjectId(post['original_author_id'])})
            
            if author and essay:
                likes = post.get('likes', [])
                likes_count = len(likes) if isinstance(likes, list) else likes
                
                comments = post.get('comments', [])
                comments_count = len(comments) if isinstance(comments, list) else comments
                
                essay_content = essay.get('content', '')
                content_preview = essay_content[:300] if essay_content else None
                
                post_data = {
                'id': str(post['_id']),
                'author_id': post['author_id'],
                'author_name': author.get('name', 'Unknown'),
                'author_email': author.get('email', ''),
                'author_avatar': author.get('avatar'),
                'essay_id': post['essay_id'],
                'essay_title': essay.get('title', 'Untitled'),
                'essay_score': essay.get('score', 0),
                'essay_content': content_preview,
                'caption': post.get('caption', ''),
                'shared_at': post.get('shared_at').isoformat() if hasattr(post.get('shared_at'), 'isoformat') else str(post.get('shared_at')),
                'visibility': post.get('visibility', 'public'),
                'likes': likes_count,
                'comments': comments_count,
                'shares': post.get('shares', 0),
                'is_share': post.get('is_share', False),
                'original_post_id': post.get('original_post_id'),
                'original_author_id': post.get('original_author_id'),
                'original_author_name': original_author.get('name', 'Unknown') if original_author else None,
                'original_author_avatar': original_author.get('avatar') if original_author else None,
                # ✅ NEW: Include the original post's upload date
                'original_shared_at': post.get('original_shared_at').isoformat() if hasattr(post.get('original_shared_at'), 'isoformat') else str(post.get('original_shared_at')),
                }

                
                result.append(post_data)
        
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

@posts_bp.route('/posts/<post_id>/comment', methods=['POST'])
def comment_post(post_id):
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
        
        # ✅ Create comment with timestamp
        comment = {
            'user_id': user_id,
            'text': comment_text,
            'created_at': datetime.now().isoformat()  # ✅ Add timestamp
        }
        
        # Add comment to post
        mongo.db.posts.update_one(
            {'_id': ObjectId(post_id)},
            {'$push': {'comments': comment}}
        )
        
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
        
        # ✅ Populate user details for each comment including avatar
        populated_comments = []
        for comment in comments:
            user = mongo.db.users.find_one({'_id': ObjectId(comment['user_id'])})
            if user:
                # ✅ Convert created_at to ISO format
                created_at = comment.get('created_at')
                if hasattr(created_at, 'isoformat'):
                    created_at = created_at.isoformat()
                else:
                    created_at = str(created_at)
                
                populated_comments.append({
                    'user_id': comment['user_id'],
                    'user_name': user.get('name', 'Unknown'),
                    'user_avatar': user.get('avatar'),
                    'text': comment['text'],
                    'created_at': created_at  # ✅ Now it's a proper ISO string
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

@posts_bp.route('/posts/<post_id>/share', methods=['POST', 'OPTIONS'])
def share_post(post_id):
    """Share/reshare a post to your feed"""
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
        share_caption = data.get('caption', '')
        
        # Get original post
        original_post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
        if not original_post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Check if user already shared this post
        existing_share = mongo.db.posts.find_one({
            'author_id': user_id,
            'original_post_id': post_id,
            'is_share': True
        })
        
        if existing_share:
            return jsonify({'error': 'You already shared this post'}), 400
        
        # Get current user details
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        # If the post being shared is already a shared post, get the ORIGINAL author info
        if original_post.get('is_share'):
            original_author_id = original_post.get('original_author_id')
            original_author_name = original_post.get('original_author_name')
            # ✅ NEW: Get the ORIGINAL post's upload date (not the share date)
            original_shared_at = original_post.get('original_shared_at')
            essay_id = original_post.get('essay_id')
        else:
            original_author_id = original_post.get('author_id')
            original_author_name = original_post.get('author_name')
            # ✅ NEW: Store the original post's upload date
            original_shared_at = original_post.get('shared_at')
            essay_id = original_post.get('essay_id')
        
        # Get essay details
        essay = mongo.db.essays.find_one({'_id': ObjectId(essay_id)})
        
        # Create shared post
        shared_post = {
            'author_id': user_id,
            'author_name': user.get('name', 'Unknown'),
            'author_email': user.get('email', ''),
            'essay_id': essay_id,
            'essay_title': essay.get('title', 'Untitled'),
            'essay_score': essay.get('score', 0),
            'caption': share_caption,
            'visibility': 'public',
            'shared_at': datetime.now(),  # This is when it was shared
            'likes': [],
            'comments': [],
            'shares': 0,
            'is_share': True,
            'original_post_id': post_id,
            'original_author_id': original_author_id,
            'original_author_name': original_author_name,
            # ✅ NEW: Store the original post's upload date
            'original_shared_at': original_shared_at,
        }
        
        result = mongo.db.posts.insert_one(shared_post)
        
        # Increment share count on original post
        mongo.db.posts.update_one(
            {'_id': ObjectId(post_id)},
            {'$inc': {'shares': 1}}
        )
        
        return jsonify({
            'message': 'Post shared successfully',
            'post_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        print(f"Error sharing post: {str(e)}")
        return jsonify({'error': str(e)}), 500

@posts_bp.route('/posts/<post_id>', methods=['PUT', 'DELETE'])
def manage_post(post_id):
    """Update or delete a post"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    # Get the post
    post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    # Check ownership
    if post['author_id'] != user_id:
        return jsonify({'error': 'You can only edit/delete your own posts'}), 403
    
    # Handle DELETE
    if request.method == 'DELETE':
        try:
            # ✅ NEW: If this is a shared post, decrement the share count of the original post
            if post.get('is_share') and post.get('original_post_id'):
                mongo.db.posts.update_one(
                    {'_id': ObjectId(post['original_post_id'])},
                    {'$inc': {'shares': -1}}
                )
            
            # ✅ NEW: If this is an original post, delete all shared posts referencing it
            if not post.get('is_share'):
                # Find all shared posts that reference this original post
                shared_posts = list(mongo.db.posts.find({
                    'original_post_id': post_id,
                    'is_share': True
                }))
                
                # Delete all shared posts
                if shared_posts:
                    mongo.db.posts.delete_many({
                        'original_post_id': post_id,
                        'is_share': True
                    })
                    print(f"Deleted {len(shared_posts)} shared posts when original post {post_id} was deleted")
            
            # Delete the post itself
            result = mongo.db.posts.delete_one({'_id': ObjectId(post_id)})
            
            if result.deleted_count > 0:
                return jsonify({'message': 'Post deleted successfully'}), 200
            else:
                return jsonify({'error': 'Failed to delete post'}), 500
        except Exception as e:
            print(f"Error deleting post: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    # Handle PUT (update)
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            new_caption = data.get('caption', '')
            
            result = mongo.db.posts.update_one(
                {'_id': ObjectId(post_id)},
                {'$set': {'caption': new_caption}}
            )
            
            if result.modified_count > 0:
                return jsonify({'message': 'Post updated successfully'}), 200
            else:
                return jsonify({'message': 'No changes made'}), 200
        except Exception as e:
            print(f"Error updating post: {str(e)}")
            return jsonify({'error': str(e)}), 500

@posts_bp.route('/posts/<post_id>/comments/<comment_index>', methods=['DELETE', 'OPTIONS'])
def delete_comment(post_id, comment_index):
    """Delete a comment from a post"""
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
        # Get the post
        post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        comments = post.get('comments', [])
        comment_idx = int(comment_index)
        
        if comment_idx < 0 or comment_idx >= len(comments):
            return jsonify({'error': 'Comment not found'}), 404
        
        # Check if user owns the comment
        comment = comments[comment_idx]
        if comment.get('user_id') != user_id:
            return jsonify({'error': 'You can only delete your own comments'}), 403
        
        # Remove the comment
        comments.pop(comment_idx)
        
        # Update the post
        mongo.db.posts.update_one(
            {'_id': ObjectId(post_id)},
            {'$set': {'comments': comments}}
        )
        
        print(f"✅ Comment deleted from post {post_id} by user {user_id}")
        return jsonify({'message': 'Comment deleted successfully'}), 200
        
    except Exception as e:
        print(f"❌ Error deleting comment: {str(e)}")
        return jsonify({'error': str(e)}), 500
