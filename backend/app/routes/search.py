from flask import Blueprint, request, jsonify
from app.models import User, Post
from app.routes.auth import verify_token
from app import mongo
from bson import ObjectId
import re

search_bp = Blueprint('search', __name__)
user_model = User(mongo.db)
post_model = Post(mongo.db)

@search_bp.route('/search', methods=['GET', 'OPTIONS'])
def global_search():
    """Search for posts and users (works for both auth and unauth users)"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    # ✅ Make authentication OPTIONAL instead of required
    user_id = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        user_id = verify_token(token)
        # Note: if token is invalid, user_id will be None (treated as unauth)
    
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'posts': [], 'users': []}), 200
    
    is_author_search = False
    search_term = query
    
    # Check if search is for author (quoted)
    quoted_match = re.match(r'^"(.+)"$', query)
    if quoted_match:
        is_author_search = True
        search_term = quoted_match.group(1).strip()
    
    # Search users (available to everyone)
    users = list(mongo.db.users.find({
        '$or': [
            {'name': {'$regex': search_term, '$options': 'i'}},
            {'email': {'$regex': search_term, '$options': 'i'}}
        ]
    }).limit(5))
    
    for user in users:
        user['_id'] = str(user['_id'])
        user['id'] = user['_id']
        if 'password_hash' in user:
            del user['password_hash']
    
    # ✅ Build post search condition based on auth status
    if is_author_search:
        post_search_condition = {'author_name': {'$regex': search_term, '$options': 'i'}}
    else:
        post_search_condition = {'essay_title': {'$regex': search_term, '$options': 'i'}}
    
    # ✅ Different visibility logic for auth vs unauth users
    if user_id:
        # Authenticated: can see own posts + public + friends-only (if friends)
        visibility_condition = {
            '$or': [
                {'author_id': user_id},  # Own posts
                {'visibility': 'public'},  # Public posts
                {
                    'visibility': 'friends',
                    'author_friends': user_id  # Friends-only posts where user is friend
                }
            ]
        }
    else:
        # ✅ Unauthenticated: can ONLY see public posts
        visibility_condition = {'visibility': 'public'}
    
    # Combine search and visibility conditions
    posts = list(mongo.db.posts.find({
        '$and': [
            post_search_condition,
            visibility_condition
        ]
    }).sort('shared_at', -1).limit(10))  # Increased limit to 10
    
    # Format posts with proper date conversion
    for post in posts:
        post['_id'] = str(post['_id'])
        post['id'] = post['_id']
        
        # Convert datetime to ISO format string
        if 'shared_at' in post and hasattr(post['shared_at'], 'isoformat'):
            post['shared_at'] = post['shared_at'].isoformat()
        else:
            post['shared_at'] = str(post.get('shared_at', ''))
        
        # ✅ Add additional fields that frontend expects
        if 'likes' in post and isinstance(post['likes'], list):
            post['likes'] = len(post['likes'])
        if 'comments' in post and isinstance(post['comments'], list):
            post['comments'] = len(post['comments'])
    
    return jsonify({
        'posts': posts,
        'users': users,
        'search_type': 'author' if is_author_search else 'title'
    }), 200
