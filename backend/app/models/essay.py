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
            
            # ✅ NEW: Atomic Statements (initially empty)
            'statements': [],
            'statement_summary': None,
            'statements_generated_at': None,
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
    
    # ✅ NEW: Add atomic statements to essay
    def add_statements(self, essay_id, statements, summary):
        """
        Add atomic statements to an essay (first-time generation)
        Called when user first views atomic statements tab
        """
        update_data = {
            'statements': statements,
            'statement_summary': summary,
            'statements_generated_at': datetime.now(),
        }
        
        result = self.collection.update_one(
            {'_id': ObjectId(essay_id)},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    # ✅ NEW: Regenerate atomic statements
    def regenerate_statements(self, essay_id, statements, summary):
        """
        Regenerate (update) atomic statements for an essay
        Called when user clicks "Regenerate" button
        """
        update_data = {
            'statements': statements,
            'statement_summary': summary,
            'statements_generated_at': datetime.now(),
        }
        
        result = self.collection.update_one(
            {'_id': ObjectId(essay_id)},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    # ✅ NEW: Check if statements exist
    def has_statements(self, essay_id):
        """
        Check if essay already has atomic statements generated
        Returns True if statements exist, False otherwise
        """
        essay = self.collection.find_one(
            {'_id': ObjectId(essay_id)},
            {'statements': 1}
        )
        
        if essay and 'statements' in essay and essay['statements']:
            return True
        return False
    
    # ✅ NEW: Get only statements (optimized query)
    def get_statements(self, essay_id):
        """
        Get only the statements and summary for an essay
        More efficient than fetching entire document
        """
        essay = self.collection.find_one(
            {'_id': ObjectId(essay_id)},
            {
                'statements': 1,
                'statement_summary': 1,
                'statements_generated_at': 1
            }
        )
        
        if essay:
            return {
                'statements': essay.get('statements', []),
                'summary': essay.get('statement_summary', {}),
                'generated_at': essay.get('statements_generated_at')
            }
        return None
    
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
