from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

class User:
    def __init__(self, db):
        self.collection = db['users']
    
    def create(self, name, email, password):
        """Create a new user"""
        # Check if user already exists
        if self.collection.find_one({'email': email}):
            return None
        
        user = {
            'name': name,
            'email': email,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.utcnow(),
            'profile_picture': None,
        }
        
        result = self.collection.insert_one(user)
        user['_id'] = str(result.inserted_id)
        del user['password_hash']  # Don't return password hash
        return user
    
    def authenticate(self, email, password):
        """Verify user credentials"""
        user = self.collection.find_one({'email': email})
        
        if user and check_password_hash(user['password_hash'], password):
            user['_id'] = str(user['_id'])
            user['id'] = user['_id']
            del user['password_hash']  # Don't return password hash
            return user
        
        return None
    
    def get_by_id(self, user_id):
        """Get user by ID"""
        user = self.collection.find_one({'_id': ObjectId(user_id)})
        if user:
            user['_id'] = str(user['_id'])
            user['id'] = user['_id']
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
