from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
import secrets

class User:
    def __init__(self, db):
        self.collection = db['users']
        self.friend_requests = db['friend_requests']
    
    def create(self, name, email, password):
        """Create a new user with email verification"""
        if self.collection.find_one({'email': email}):
            return None
        
        # ✅ Generate verification token
        verification_token = secrets.token_urlsafe(32)
        
        user = {
            'name': name,
            'email': email,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.now(timezone.utc),
            'avatar': None,  # ✅ Add default avatar
            'location': None,  # ✅ Add location field
            'bio': None,  # ✅ Add bio field
            'friends': [],
            'is_verified': False,  # ✅ Email verification status
            'verification_token': verification_token,  # ✅ Verification token
            'verification_token_expires': None  # ✅ Optional: token expiry
        }
        
        result = self.collection.insert_one(user)
        user['_id'] = str(result.inserted_id)
        user['id'] = user['_id']
        del user['password_hash']
        
        return user
    
    def authenticate(self, email, password):
        """Verify user credentials and check if verified"""
        user = self.collection.find_one({'email': email})
        
        if not user or not check_password_hash(user['password_hash'], password):
            return None
        
        # ✅ Check if email is verified
        if not user.get('is_verified', False):
            return {'error': 'Please verify your email first', 'verified': False}
        
        user['_id'] = str(user['_id'])
        user['id'] = user['_id']
        del user['password_hash']
        
        return user
    
    def verify_email(self, token):
        """Verify user email with token"""
        user = self.collection.find_one({'verification_token': token})
        
        if not user:
            return None
        
        # Mark as verified
        self.collection.update_one(
            {'_id': user['_id']},
            {'$set': {
                'is_verified': True,
                'verification_token': None  # Remove token after use
            }}
        )
        
        return True
    
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
        print(f"🔵 send_friend_request: from={from_user_id}, to={to_user_id}")
        
        from_user = self.collection.find_one({'_id': ObjectId(from_user_id)})
        if to_user_id in from_user.get('friends', []):
            print(f"⚠️ Already friends")
            return {'error': 'Already friends'}
        
        existing = self.friend_requests.find_one({
            '$or': [
                {'from_user_id': from_user_id, 'to_user_id': to_user_id},
                {'from_user_id': to_user_id, 'to_user_id': from_user_id}
            ]
        })
        
        if existing:
            print(f"📋 Found existing request: {existing}")
            if existing['status'] == 'pending':
                if existing['from_user_id'] == to_user_id:
                    print(f"✅ Auto-accepting mutual request")
                    self.accept_friend_request(str(existing['_id']), from_user_id)
                    return {'message': 'Friend request auto-accepted'}
                print(f"⚠️ Request already sent")
                return {'error': 'Friend request already sent'}
            elif existing['status'] == 'accepted':
                print(f"⚠️ Already friends (accepted)")
                return {'error': 'Already friends'}
        
        request = {
            'from_user_id': from_user_id,
            'to_user_id': to_user_id,
            'status': 'pending',
            'created_at': datetime.now(timezone.utc)
        }
        
        print(f"✅ Creating request: {request}")
        result = self.friend_requests.insert_one(request)
        print(f"✅ Request created with ID: {result.inserted_id}")
        return {'message': 'Friend request sent', 'request_id': str(result.inserted_id)}
    
    def get_pending_requests(self, user_id):
        """Get pending friend requests for user (where they are the receiver)"""
        print(f"🔍 get_pending_requests for user: {user_id}")
        
        requests = list(self.friend_requests.find({
            'to_user_id': user_id,
            'status': 'pending'
        }).sort('created_at', -1))
        
        print(f"📊 Found {len(requests)} pending requests")
        
        result = []
        for req in requests:
            sender_id = req.get('from_user_id')
            if not sender_id:
                print(f"⚠️ Request missing from_user_id: {req}")
                continue
            
            sender = self.get_by_id(sender_id)
            if sender:
                print(f"👤 Sender info: name={sender.get('name')}, avatar={sender.get('avatar')}")
                result.append({
                    '_id': str(req['_id']),
                    'from_user_id': sender_id,
                    'sender': {
                        'id': sender['id'],
                        'name': sender.get('name', 'Unknown'),
                        'email': sender.get('email', ''),
                        'avatar': sender.get('avatar')
                    },
                    'created_at': req.get('created_at'),
                    'status': req.get('status')
                })
                print(f"✅ Added request from {sender.get('name')} with avatar: {sender.get('avatar')}")
        
        print(f"✅ Returning {len(result)} requests")
        return result
    
    def accept_friend_request(self, request_id, user_id):
        """Accept a friend request"""
        print(f"✅ accept_friend_request: request_id={request_id}, user_id={user_id}")
        
        request = self.friend_requests.find_one({'_id': ObjectId(request_id)})
        
        if not request:
            print(f"❌ Request not found")
            return {'error': 'Request not found'}
        
        if request.get('to_user_id') != user_id:
            print(f"❌ Unauthorized: to_user_id={request.get('to_user_id')}, user_id={user_id}")
            return {'error': 'Unauthorized'}
        
        if request['status'] != 'pending':
            print(f"❌ Request already processed")
            return {'error': 'Request already processed'}
        
        self.friend_requests.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': {
                'status': 'accepted', 
                'accepted_at': datetime.now(timezone.utc)
            }}
        )
        
        self.collection.update_one(
            {'_id': ObjectId(request['from_user_id'])},
            {'$addToSet': {'friends': request['to_user_id']}}
        )
        self.collection.update_one(
            {'_id': ObjectId(request['to_user_id'])},
            {'$addToSet': {'friends': request['from_user_id']}}
        )
        
        print(f"✅ Friend request accepted")
        return {'message': 'Friend request accepted'}
    
    def reject_friend_request(self, request_id, user_id):
        """Reject a friend request"""
        print(f"❌ reject_friend_request: request_id={request_id}, user_id={user_id}")
        
        request = self.friend_requests.find_one({'_id': ObjectId(request_id)})
        
        if not request:
            print(f"❌ Request not found")
            return {'error': 'Request not found'}
        
        if request.get('to_user_id') != user_id:
            print(f"❌ Unauthorized")
            return {'error': 'Unauthorized'}
        
        self.friend_requests.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': {
                'status': 'rejected', 
                'rejected_at': datetime.now(timezone.utc)
            }}
        )
        
        print(f"✅ Friend request rejected")
        return {'message': 'Friend request rejected'}
    
    def get_friend_suggestions(self, user_id, limit=10):
        """Get friend suggestions (users not yet friends)"""
        user = self.collection.find_one({'_id': ObjectId(user_id)})
        friend_ids = user.get('friends', [])
        
        pending_requests = list(self.friend_requests.find({
            '$or': [
                {'from_user_id': user_id, 'status': 'pending'},
                {'to_user_id': user_id, 'status': 'pending'}
            ]
        }))
        
        excluded_ids = friend_ids + [user_id]
        for req in pending_requests:
            if req.get('from_user_id'):
                excluded_ids.append(req['from_user_id'])
            if req.get('to_user_id'):
                excluded_ids.append(req['to_user_id'])
        
        suggestions = list(self.collection.find({
            '_id': {'$nin': [ObjectId(uid) for uid in excluded_ids if uid and ObjectId.is_valid(uid)]}
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
