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
    """Search for posts and users"""
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
    
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'posts': [], 'users': []}), 200
    
    # ✅ NEW: Check if query is wrapped in quotes for author search
    is_author_search = False
    search_term = query
    
    # Detect quoted strings: "author name"
    quoted_match = re.match(r'^"(.+)"$', query)
    if quoted_match:
        is_author_search = True
        search_term = quoted_match.group(1).strip()
    
    # Search users by name or email
    users = list(mongo.db.users.find({
        '$or': [
            {'name': {'$regex': search_term, '$options': 'i'}},
            {'email': {'$regex': search_term, '$options': 'i'}}
        ]
    }).limit(5))
    
    # Format users
    for user in users:
        user['_id'] = str(user['_id'])
        user['id'] = user['_id']
        if 'password_hash' in user:
            del user['password_hash']
    
    # ✅ UPDATED: Search posts by essay_title OR author_name (if quoted)
    if is_author_search:
        # Search by author name only
        post_search_condition = {'author_name': {'$regex': search_term, '$options': 'i'}}
    else:
        # Search by essay title only
        post_search_condition = {'essay_title': {'$regex': search_term, '$options': 'i'}}
    
    posts = list(mongo.db.posts.find({
        '$and': [
            post_search_condition,
            
            # Visibility condition
            {
                '$or': [
                    {'author_id': user_id},
                    {'visibility': 'public'},
                    {
                        'visibility': 'friends',
                        'author_friends': user_id
                    }
                ]
            }
        ]
    }).sort('shared_at', -1).limit(5))
    
    # Format posts
    for post in posts:
        post['_id'] = str(post['_id'])
        post['id'] = post['_id']
    
    return jsonify({
        'posts': posts,
        'users': users,
        'search_type': 'author' if is_author_search else 'title'  # Optional: tell frontend what type of search
    }), 200
