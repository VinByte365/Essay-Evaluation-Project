from datetime import datetime
from bson import ObjectId

class Essay:
    def __init__(self, db):
        self.collection = db['essays']
    
    def create(self, user_id, title, content, file_name=None):
        """Create a new essay with 'evaluating' status"""
        essay = {
            'user_id': user_id,
            'title': title,
            'content': content,
            'file_name': file_name,
            'upload_date': datetime.now(),
            'status': 'evaluating',
            'score': None,
            'feedback': None,
            'grammar_errors': None,
            'linguistic_stats': None,
            'ai_detection': None,
        }
        result = self.collection.insert_one(essay)
        essay['_id'] = str(result.inserted_id)
        return essay
    
    def update_evaluation(self, essay_id, evaluation_results):
        """Update essay with evaluation results"""
        update_data = {
            'status': 'completed',
            'score': evaluation_results.get('score'),
            'feedback': evaluation_results.get('feedback'),
            'grammar_errors': evaluation_results.get('total_grammar_errors'),
            'linguistic_stats': {
                'num_sentences': evaluation_results.get('num_sentences'),
                'num_tokens': evaluation_results.get('num_tokens'),
                'num_entities': evaluation_results.get('num_entities'),
                'avg_sentence_length': evaluation_results.get('avg_sentence_length'),
            },
            'ai_detection': {
                'label': evaluation_results.get('ai_detection_label'),
                'score': evaluation_results.get('ai_detection_score'),
            },
            'error_feedback': evaluation_results.get('error_feedback', []),
            'evaluated_at': datetime.now(),
        }
        
        self.collection.update_one(
            {'_id': ObjectId(essay_id)},
            {'$set': update_data}
        )
        
        return self.get_by_id(essay_id)
    
    def get_by_id(self, essay_id):
        """Get essay by ID"""
        essay = self.collection.find_one({'_id': ObjectId(essay_id)})
        if essay:
            essay['_id'] = str(essay['_id'])
            essay['id'] = essay['_id']
        return essay
    
    def get_by_user(self, user_id, limit=20):
        """Get all essays for a user"""
        essays = list(self.collection.find(
            {'user_id': user_id}
        ).sort('upload_date', -1).limit(limit))
        
        for essay in essays:
            essay['_id'] = str(essay['_id'])
            essay['id'] = essay['_id']
        
        return essays
    
    def delete(self, essay_id):
        """Delete an essay"""
        self.collection.delete_one({'_id': ObjectId(essay_id)})
