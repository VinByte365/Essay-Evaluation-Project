from datetime import datetime
from bson import ObjectId

class Notification:
    def __init__(self, db):
        self.collection = db['notifications']
    
    def create(self, user_id, notification_type, data):
        """
        Create a notification
        
        Types:
        - 'like': Someone liked your post
        - 'comment': Someone commented on your post
        - 'friend_request': Someone sent you a friend request
        - 'friend_accept': Someone accepted your friend request
        - 'share': Someone shared your post
        """
        notification = {
            'user_id': user_id,
            'type': notification_type,
            'data': data,
            'read': False,
            'created_at': datetime.now()
        }
        
        result = self.collection.insert_one(notification)
        notification['_id'] = str(result.inserted_id)
        return notification
    
    def get_user_notifications(self, user_id, limit=20, unread_only=False):
        """Get notifications for a user"""
        query = {'user_id': user_id}
        if unread_only:
            query['read'] = False
        
        notifications = list(
            self.collection.find(query)
            .sort('created_at', -1)
            .limit(limit)
        )
        
        for notif in notifications:
            notif['_id'] = str(notif['_id'])
            notif['id'] = notif['_id']
            
            # ✅ Convert datetime to ISO format string
            if 'created_at' in notif:
                if hasattr(notif['created_at'], 'isoformat'):
                    notif['created_at'] = notif['created_at'].isoformat()
                else:
                    # If it's already a string, keep it
                    notif['created_at'] = str(notif['created_at'])
        
        return notifications
    
    def mark_as_read(self, notification_id):
        """Mark a notification as read"""
        self.collection.update_one(
            {'_id': ObjectId(notification_id)},
            {'$set': {'read': True}}
        )
    
    def mark_all_as_read(self, user_id):
        """Mark all notifications as read for a user"""
        self.collection.update_many(
            {'user_id': user_id, 'read': False},
            {'$set': {'read': True}}
        )
    
    def get_unread_count(self, user_id):
        """Get count of unread notifications"""
        return self.collection.count_documents({
            'user_id': user_id,
            'read': False
        })
    
    def delete(self, notification_id):
        """Delete a notification"""
        self.collection.delete_one({'_id': ObjectId(notification_id)})
