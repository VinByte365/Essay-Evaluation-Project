from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId


class User:
    def __init__(self, db):
        self.collection = db['users']
        self.friend_requests = db['friend_requests']  # NEW: Separate collection
    
    def create(self, name, email, password):
        """Create a new user"""
        if self.collection.find_one({'email': email}):
            return None
        
        user = {
            'name': name,
            'email': email,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.utcnow(),
            'profile_picture': None,
            'friends': [],  # Array of friend user IDs (accepted friends only)
        }
        
        result = self.collection.insert_one(user)
        user['_id'] = str(result.inserted_id)
        del user['password_hash']
        return user
    
    def authenticate(self, email, password):
        """Verify user credentials"""
        user = self.collection.find_one({'email': email})
        
        if user and check_password_hash(user['password_hash'], password):
            user['_id'] = str(user['_id'])
            user['id'] = user['_id']
            del user['password_hash']
            return user
        
        return None
    
    def get_by_id(self, user_id):
        """Get user by ID"""
        user = self.collection.find_one({'_id': ObjectId(user_id)})
        if user:
            user['_id'] = str(user['_id'])
            user['id'] = user['_id']
            if 'password_hash' in user:
                del user['password_hash']
        return user
    
    def get_by_email(self, email):
        """Get user by email"""
        user = self.collection.find_one({'email': email})
        if user:
            user['_id'] = str(user['_id'])
            user['id'] = user['_id']
            if 'password_hash' in user:
                del user['password_hash']
        return user
    
    # ========== FRIEND REQUEST SYSTEM ==========
    
    def send_friend_request(self, from_user_id, to_user_id):
        """Send a friend request"""
        # Check if already friends
        from_user = self.collection.find_one({'_id': ObjectId(from_user_id)})
        if to_user_id in from_user.get('friends', []):
            return {'error': 'Already friends'}
        
        # Check if request already exists
        existing = self.friend_requests.find_one({
            '$or': [
                {'from_user_id': from_user_id, 'to_user_id': to_user_id},
                {'from_user_id': to_user_id, 'to_user_id': from_user_id}
            ]
        })
        
        if existing:
            if existing['status'] == 'pending':
                # If the other user already sent a request, auto-accept it
                if existing['from_user_id'] == to_user_id:
                    self.accept_friend_request(existing['_id'], from_user_id)
                    return {'message': 'Friend request auto-accepted'}
                return {'error': 'Friend request already sent'}
            elif existing['status'] == 'accepted':
                return {'error': 'Already friends'}
        
        # Create new friend request
        request = {
            'from_user_id': from_user_id,
            'to_user_id': to_user_id,
            'status': 'pending',
            'created_at': datetime.utcnow()
        }
        
        result = self.friend_requests.insert_one(request)
        return {'message': 'Friend request sent', 'request_id': str(result.inserted_id)}
    
    def accept_friend_request(self, request_id, user_id):
        """Accept a friend request"""
        request = self.friend_requests.find_one({'_id': ObjectId(request_id)})
        
        if not request:
            return {'error': 'Request not found'}
        
        if request['to_user_id'] != user_id:
            return {'error': 'Unauthorized'}
        
        if request['status'] != 'pending':
            return {'error': 'Request already processed'}
        
        # Update request status
        self.friend_requests.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': {'status': 'accepted', 'accepted_at': datetime.utcnow()}}
        )
        
        # Add each other as friends
        self.collection.update_one(
            {'_id': ObjectId(request['from_user_id'])},
            {'$addToSet': {'friends': request['to_user_id']}}
        )
        self.collection.update_one(
            {'_id': ObjectId(request['to_user_id'])},
            {'$addToSet': {'friends': request['from_user_id']}}
        )
        
        return {'message': 'Friend request accepted'}
    
    def reject_friend_request(self, request_id, user_id):
        """Reject a friend request"""
        request = self.friend_requests.find_one({'_id': ObjectId(request_id)})
        
        if not request:
            return {'error': 'Request not found'}
        
        if request['to_user_id'] != user_id:
            return {'error': 'Unauthorized'}
        
        # Update status or delete
        self.friend_requests.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': {'status': 'rejected', 'rejected_at': datetime.utcnow()}}
        )
        
        return {'message': 'Friend request rejected'}
    
    def get_pending_requests(self, user_id):
        """Get pending friend requests for user"""
        requests = list(self.friend_requests.find({
            'to_user_id': user_id,
            'status': 'pending'
        }).sort('created_at', -1))
        
        # Populate sender details
        for req in requests:
            req['_id'] = str(req['_id'])
            sender = self.get_by_id(req['from_user_id'])
            req['sender'] = sender
        
        return requests
    
    def get_friend_suggestions(self, user_id, limit=10):
        """Get friend suggestions (users not yet friends)"""
        user = self.collection.find_one({'_id': ObjectId(user_id)})
        friend_ids = user.get('friends', [])
        
        # Get pending requests to exclude
        pending_requests = list(self.friend_requests.find({
            '$or': [
                {'from_user_id': user_id, 'status': 'pending'},
                {'to_user_id': user_id, 'status': 'pending'}
            ]
        }))
        
        excluded_ids = friend_ids + [user_id]
        for req in pending_requests:
            excluded_ids.append(req['from_user_id'])
            excluded_ids.append(req['to_user_id'])
        
        # Find users not in excluded list
        suggestions = list(self.collection.find({
            '_id': {'$nin': [ObjectId(uid) for uid in excluded_ids if ObjectId.is_valid(uid)]}
        }).limit(limit))
        
        for user in suggestions:
            user['_id'] = str(user['_id'])
            user['id'] = user['_id']
            if 'password_hash' in user:
                del user['password_hash']
        
        return suggestions
    
    def search_users(self, query, limit=10):
        """Search users by name or email"""
        users = list(self.collection.find({
            '$or': [
                {'name': {'$regex': query, '$options': 'i'}},
                {'email': {'$regex': query, '$options': 'i'}}
            ]
        }).limit(limit))
        
        for user in users:
            user['_id'] = str(user['_id'])
            user['id'] = user['_id']
            if 'password_hash' in user:
                del user['password_hash']
        
        return users
