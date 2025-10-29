from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId


class User:
    def __init__(self, db):
        self.collection = db['users']
        self.friend_requests = db['friend_requests']
    
    def create(self, name, email, password):
        """Create a new user"""
        if self.collection.find_one({'email': email}):
            return None
        
        user = {
            'name': name,
            'email': email,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.now(timezone.utc),
            'friends': [],
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
            # Avatar should be included automatically if it exists
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
        
        # ✅ FIXED: Use to_user_id instead of receiver_id
        requests = list(self.friend_requests.find({
            'to_user_id': user_id,
            'status': 'pending'
        }).sort('created_at', -1))
        
        print(f"📊 Found {len(requests)} pending requests")
        
        # Populate sender details
        result = []
        for req in requests:
            # ✅ FIXED: Use from_user_id instead of sender_id
            sender_id = req.get('from_user_id')
            if not sender_id:
                print(f"⚠️ Request missing from_user_id: {req}")
                continue
            
            sender = self.get_by_id(sender_id)
            if sender:
                print(f"👤 Sender info: name={sender.get('name')}, avatar={sender.get('avatar')}")  # Debug log
                result.append({
                    '_id': str(req['_id']),
                    'from_user_id': sender_id,
                    'sender': {
                        'id': sender['id'],
                        'name': sender.get('name', 'Unknown'),
                        'email': sender.get('email', ''),
                        'avatar': sender.get('avatar')  # ✅ Make sure this is included
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
        
        # ✅ FIXED: Use to_user_id instead of receiver_id
        if request.get('to_user_id') != user_id:
            print(f"❌ Unauthorized: to_user_id={request.get('to_user_id')}, user_id={user_id}")
            return {'error': 'Unauthorized'}
        
        if request['status'] != 'pending':
            print(f"❌ Request already processed")
            return {'error': 'Request already processed'}
        
        # Update request status
        self.friend_requests.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': {
                'status': 'accepted', 
                'accepted_at': datetime.now(timezone.utc)
            }}
        )
        
        # ✅ FIXED: Use from_user_id and to_user_id instead of sender_id/receiver_id
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
        
        # ✅ FIXED: Use to_user_id instead of receiver_id
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
        
        # ✅ FIXED: Use from_user_id and to_user_id
        pending_requests = list(self.friend_requests.find({
            '$or': [
                {'from_user_id': user_id, 'status': 'pending'},
                {'to_user_id': user_id, 'status': 'pending'}
            ]
        }))
        
        excluded_ids = friend_ids + [user_id]
        for req in pending_requests:
            # ✅ FIXED: Use from_user_id and to_user_id
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
    