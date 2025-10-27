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
        
        result = self.collection.insert_one(post)
        post['_id'] = str(result.inserted_id)
        return post
    
    def get_feed(self, user_id, limit=50):
        """Get posts for user's feed (public + friends' posts)"""
        # For now, return all public posts
        # TODO: Add friends logic
        posts = list(self.collection.find(
            {'visibility': 'public'}
        ).sort('shared_at', -1).limit(limit))
        
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
