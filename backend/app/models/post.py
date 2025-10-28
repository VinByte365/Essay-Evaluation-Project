from datetime import datetime
from bson import ObjectId


class Post:
    def __init__(self, db):
        self.collection = db['posts']
    
    def create(self, author_id, author_name, author_email, essay_id, essay_title, essay_score, caption, visibility):
        """Create a new post"""
        post = {
            'author_id': author_id,
            'author_name': author_name,
            'author_email': author_email,
            'essay_id': essay_id,
            'essay_title': essay_title,
            'essay_score': essay_score,
            'caption': caption,
            'visibility': visibility,
            'shared_at': datetime.utcnow(),
            'likes': 0,
            'comments': [],
            'shares': 0,
        }
        
        # If friends-only post, store the author's friends list
        if visibility == "friends":
            from app.models import User
            user_model = User(self.collection.database)
            user = user_model.get_by_id(author_id)
            post['author_friends'] = user.get('friends', [])  # Array of friend user IDs
        
        result = self.collection.insert_one(post)
        post['_id'] = str(result.inserted_id)
        return post
    
    def get_feed(self, user_id, limit=50):
        """Get posts for user's feed (own posts + public + friends' posts)"""
        from bson import ObjectId
        
        # Convert user_id to ObjectId if it's a string
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Query: Show user's own posts + public posts + friends-only posts where user is a friend
        posts = list(self.collection.find({
            "$or": [
                {"author_id": str(user_id)},      # User's own posts (all visibility levels)
                {"visibility": "public"},          # Public posts from everyone
                {
                    "visibility": "friends",       # Friends-only posts
                    "author_friends": str(user_id) # Where current user is in friends list
                }
            ]
        }).sort('shared_at', -1).limit(limit))
        
        for post in posts:
            post['_id'] = str(post['_id'])
            post['id'] = post['_id']
        
        return posts
    
    def get_by_user(self, user_id, limit=20):
        """Get posts by specific user"""
        posts = list(self.collection.find(
            {'author_id': user_id}
        ).sort('shared_at', -1).limit(limit))
        
        for post in posts:
            post['_id'] = str(post['_id'])
            post['id'] = post['_id']
        
        return posts
    
    def like_post(self, post_id):
        """Increment likes"""
        self.collection.update_one(
            {'_id': ObjectId(post_id)},
            {'$inc': {'likes': 1}}
        )
    
    def add_comment(self, post_id, user_id, user_name, comment_text):
        """Add comment to post"""
        comment = {
            'user_id': user_id,
            'user_name': user_name,
            'text': comment_text,
            'created_at': datetime.utcnow()
        }
        
        self.collection.update_one(
            {'_id': ObjectId(post_id)},
            {'$push': {'comments': comment}, '$inc': {'comment_count': 1}}
        )
