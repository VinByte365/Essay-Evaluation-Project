from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import spacy
from app.models.essay import Essay
from bson import ObjectId
from app.routes.auth import verify_token 
from datetime import datetime

api_bp = Blueprint('api', __name__)

# Initialize NLP tools
nlp = spacy.load("en_core_web_sm")

# Initialize MongoDB
from app import mongo
essay_model = Essay(mongo.db)

# Import LLM service
try:
    from app.services.llm_service import llm_service
    LLM_AVAILABLE = True
except Exception as e:
    print(f"Warning: LLM service not available: {e}")
    LLM_AVAILABLE = False

def extract_text_from_docx(file_stream):
    """Extract text from DOCX file"""
    try:
        from docx import Document
        doc = Document(file_stream)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        print(f"Error extracting DOCX: {e}")
        raise Exception("Failed to read DOCX file")

@api_bp.route('/upload-essay', methods=['POST', 'OPTIONS'])
def upload_essay():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
        
        token = auth_header.split(' ')[1]
        user_id = verify_token(token)
        
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        print(f"📝 Uploading essay for user: {user_id}")
        
        # Validate file
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Extract text
        if file.filename.endswith('.txt'):
            text = file.read().decode('utf-8')
        elif file.filename.endswith('.docx'):
            text = extract_text_from_docx(file.stream)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        if not text or len(text.strip()) < 10:
            return jsonify({'error': 'Text is too short'}), 400
        
        title = file.filename.rsplit('.', 1)[0]
        
        # Create essay record first
        essay = essay_model.create(
            user_id=user_id,
            title=title,
            content=text,
            file_name=secure_filename(file.filename)
        )
        
        essay_id = essay['_id']
        print(f"✅ Essay created with ID: {essay_id}")
        
        # Check if LLM is available
        if not LLM_AVAILABLE:
            print("⚠️ LLM service not available")
            return jsonify({
                'essay_id': essay_id,
                'score': 0,
                'feedback': 'AI evaluation service is not available. Please check HUGGINGFACE_API_TOKEN.',
                'total_grammar_errors': 0,
                'error_feedback': [],
                'num_sentences': 0,
                'num_tokens': 0,
                'num_entities': 0,
                'avg_sentence_length': 0,
                'ai_detection_label': 'Not analyzed',
                'ai_detection_score': 0
            }), 200
        
        # Perform AI evaluation
        print(f"🤖 Starting AI evaluation for: {title}")
        evaluation = llm_service.evaluate_essay(title=title, content=text)
        
        print(f"✅ AI Evaluation received - Score: {evaluation.get('score', 'N/A')}")
        print(f"   Grammar errors: {evaluation.get('total_grammar_errors', 0)}")
        print(f"   AI Detection: {evaluation.get('ai_detection_label', 'N/A')}")
        
        # Update essay in database
        mongo.db.essays.update_one(
            {'_id': ObjectId(essay_id)},
            {
                '$set': {
                    'status': 'completed',
                    'score': evaluation['score'],
                    'feedback': evaluation['feedback'],
                    'grammar': evaluation.get('grammar', ''),
                    'structure': evaluation.get('structure', ''),
                    'content_quality': evaluation.get('content', ''),
                    'coherence': evaluation.get('coherence', ''),
                    'suggestions': evaluation.get('suggestions', []),
                    'total_grammar_errors': evaluation['total_grammar_errors'],
                    'error_feedback': evaluation['error_feedback'],
                    'num_sentences': evaluation['num_sentences'],
                    'num_tokens': evaluation['num_tokens'],
                    'avg_sentence_length': evaluation['avg_sentence_length'],
                    'ai_detection_label': evaluation['ai_detection_label'],
                    'ai_detection_score': evaluation['ai_detection_score'],
                    'ai_evaluated': True,
                    'evaluated_at': datetime.now()
                }
            }
        )
        
        # Return AI evaluation results to frontend
        result = {
            'essay_id': essay_id,
            'score': evaluation['score'],
            'feedback': evaluation['feedback'],
            'grammar': evaluation.get('grammar', ''),
            'structure': evaluation.get('structure', ''),
            'content': evaluation.get('content', ''),
            'coherence': evaluation.get('coherence', ''),
            'suggestions': evaluation.get('suggestions', []),
            'total_grammar_errors': evaluation['total_grammar_errors'],
            'error_feedback': evaluation['error_feedback'],
            'num_sentences': evaluation['num_sentences'],
            'num_tokens': evaluation['num_tokens'],
            'num_entities': 0,
            'avg_sentence_length': evaluation['avg_sentence_length'],
            'ai_detection_label': evaluation['ai_detection_label'],
            'ai_detection_score': evaluation['ai_detection_score']
        }
        
        print(f"📤 Sending response to frontend")
        return jsonify(result), 200
        
    except Exception as e:
        print(f"❌ Error in upload_essay: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/essays', methods=['GET', 'OPTIONS'])
def get_essays():
    """Get all essays for current user"""
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
    
    print(f"Fetching essays for user: {user_id}")
    
    try:

        essays = list(mongo.db.essays.find({'user_id': user_id}).sort('upload_date', -1))
        
 
        formatted_essays = []
        for essay in essays:
            upload_date = essay.get('upload_date')
            if hasattr(upload_date, 'isoformat'):
                upload_date_str = upload_date.isoformat()
            else:
                upload_date_str = str(upload_date) if upload_date else None
            
            evaluated_at = essay.get('evaluated_at')
            if hasattr(evaluated_at, 'isoformat'):
                evaluated_at_str = evaluated_at.isoformat()
            else:
                evaluated_at_str = str(evaluated_at) if evaluated_at else None
            
            formatted_essay = {
                'id': str(essay['_id']),
                'title': essay.get('title', 'Untitled'),
                'content': essay.get('content', ''),  
                'upload_date': upload_date_str,
                'status': essay.get('status', 'pending'),
                'score': essay.get('score', 0),
                'feedback': essay.get('feedback', ''),
                'grammar': essay.get('grammar', ''),
                'structure': essay.get('structure', ''),
                'content_quality': essay.get('content_quality', ''),
                'coherence': essay.get('coherence', ''),
                'suggestions': essay.get('suggestions', []),
                'total_grammar_errors': essay.get('total_grammar_errors', 0),
                'ai_evaluated': essay.get('ai_evaluated', False),
                'evaluated_at': evaluated_at_str
            }
            formatted_essays.append(formatted_essay)
        
        print(f"📄 Found {len(formatted_essays)} essays")
        return jsonify({'essays': formatted_essays}), 200
        
    except Exception as e:
        print(f"Error fetching essays: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/essays/<essay_id>', methods=['GET', 'DELETE', 'OPTIONS'])
def handle_essay(essay_id):
    """Get or delete a specific essay - GET allows unauthenticated access for public posts"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, DELETE, OPTIONS')
        return response, 200
    
    # Handle GET request - Allow unauthenticated access for public posts
    if request.method == 'GET':
        try:
            # Try to get user_id if authenticated (optional)
            user_id = None
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                user_id = verify_token(token)
            
            # Validate essay_id format
            if not ObjectId.is_valid(essay_id):
                return jsonify({'error': 'Invalid essay ID format'}), 400
            
            essay = mongo.db.essays.find_one({'_id': ObjectId(essay_id)})
            
            if not essay:
                return jsonify({'error': 'Essay not found'}), 404
            
            # If user owns the essay, grant full access
            if user_id and essay['user_id'] == user_id:
                essay_data = {
                    'id': str(essay['_id']),
                    'title': essay.get('title', 'Untitled'),
                    'content': essay.get('content', ''),
                    'upload_date': essay.get('upload_date'),
                    'status': essay.get('status', 'completed'),
                    'score': essay.get('score'),
                    'feedback': essay.get('feedback'),
                    'grammar': essay.get('grammar'),
                    'structure': essay.get('structure'),
                    'content_quality': essay.get('content_quality'),
                    'coherence': essay.get('coherence'),
                    'suggestions': essay.get('suggestions', []),
                    'user_id': essay.get('user_id')
                }
                return jsonify(essay_data), 200
            
            # Check if essay has been shared as a post
            post = mongo.db.posts.find_one({'essay_id': essay_id})
            
            if not post:
                return jsonify({'error': 'Essay not available publicly'}), 403
            
            # Check post visibility
            if post['visibility'] == 'public':
                # Public post - anyone can view (authenticated or not)
                essay_data = {
                    'id': str(essay['_id']),
                    'title': essay.get('title', 'Untitled'),
                    'content': essay.get('content', ''),
                    'upload_date': essay.get('upload_date'),
                    'status': essay.get('status', 'completed'),
                    'score': essay.get('score'),
                    'feedback': essay.get('feedback'),
                    'grammar': essay.get('grammar'),
                    'structure': essay.get('structure'),
                    'content_quality': essay.get('content_quality'),
                    'coherence': essay.get('coherence'),
                    'suggestions': essay.get('suggestions', []),
                    'user_id': essay.get('user_id')
                }
                return jsonify(essay_data), 200
            
            elif post['visibility'] == 'friends':
                # Friends-only post - require authentication
                if not user_id:
                    return jsonify({'error': 'Authentication required for friends-only content'}), 401
                
                current_user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
                if not current_user:
                    return jsonify({'error': 'User not found'}), 404
                
                friends_list = current_user.get('friends', [])
                
                if post['author_id'] not in friends_list:
                    return jsonify({'error': 'Friends only'}), 403
                
                essay_data = {
                    'id': str(essay['_id']),
                    'title': essay.get('title', 'Untitled'),
                    'content': essay.get('content', ''),
                    'upload_date': essay.get('upload_date'),
                    'status': essay.get('status', 'completed'),
                    'score': essay.get('score'),
                    'feedback': essay.get('feedback'),
                    'grammar': essay.get('grammar'),
                    'structure': essay.get('structure'),
                    'content_quality': essay.get('content_quality'),
                    'coherence': essay.get('coherence'),
                    'suggestions': essay.get('suggestions', []),
                    'user_id': essay.get('user_id')
                }
                return jsonify(essay_data), 200
            
            else:
                return jsonify({'error': 'Unauthorized'}), 403
            
        except Exception as e:
            print(f"Error fetching essay: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 400
    
    # Handle DELETE request - Requires authentication
    elif request.method == 'DELETE':
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
        
        token = auth_header.split(' ')[1]
        user_id = verify_token(token)
        
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        try:
            essay = mongo.db.essays.find_one({'_id': ObjectId(essay_id)})
            
            if not essay:
                return jsonify({'error': 'Essay not found'}), 404
            
            if essay['user_id'] != user_id:
                return jsonify({'error': 'Unauthorized'}), 403
            
            # Delete associated posts
            deleted_posts = mongo.db.posts.delete_many({'essay_id': essay_id})
            print(f"🗑️ Deleted {deleted_posts.deleted_count} posts associated with essay {essay_id}")
            
            # Delete essay
            mongo.db.essays.delete_one({'_id': ObjectId(essay_id)})
            
            return jsonify({
                'message': 'Essay deleted successfully',
                'deleted_posts': deleted_posts.deleted_count
            }), 200
            
        except Exception as e:
            print(f"Error deleting essay: {str(e)}")
            return jsonify({'error': str(e)}), 500

@api_bp.route('/essays/<essay_id>/evaluate', methods=['POST', 'OPTIONS'])
def evaluate_essay(essay_id):
    """Re-evaluate an existing essay with AI"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    if not LLM_AVAILABLE:
        return jsonify({'error': 'AI evaluation service is not available'}), 503
    
    try:
        essay = mongo.db.essays.find_one({
            '_id': ObjectId(essay_id),
            'user_id': user_id
        })
        
        if not essay:
            return jsonify({'error': 'Essay not found'}), 404
        
        if essay.get('ai_evaluated'):
            return jsonify({
                'message': 'Essay already evaluated',
                'evaluation': {
                    'score': essay.get('score'),
                    'feedback': essay.get('feedback'),
                    'grammar': essay.get('grammar'),
                    'structure': essay.get('structure'),
                    'content': essay.get('content_quality'),
                    'coherence': essay.get('coherence'),
                    'suggestions': essay.get('suggestions', []),
                    'total_grammar_errors': essay.get('total_grammar_errors', 0),
                    'error_feedback': essay.get('error_feedback', []),
                    'ai_detection_label': essay.get('ai_detection_label'),
                    'ai_detection_score': essay.get('ai_detection_score'),
                    'num_sentences': essay.get('num_sentences'),
                    'num_tokens': essay.get('num_tokens'),
                    'avg_sentence_length': essay.get('avg_sentence_length')
                }
            }), 200
        
        print(f"Re-evaluating essay: {essay.get('title')}")
        evaluation = llm_service.evaluate_essay(
            title=essay.get('title', 'Untitled'),
            content=essay.get('content', '')
        )
        
        mongo.db.essays.update_one(
            {'_id': ObjectId(essay_id)},
            {
                '$set': {
                    'status': 'completed',
                    'score': evaluation['score'],
                    'feedback': evaluation['feedback'],
                    'grammar': evaluation.get('grammar'),
                    'structure': evaluation.get('structure'),
                    'content_quality': evaluation.get('content'),
                    'coherence': evaluation.get('coherence'),
                    'suggestions': evaluation.get('suggestions', []),
                    'total_grammar_errors': evaluation['total_grammar_errors'],
                    'error_feedback': evaluation['error_feedback'],
                    'num_sentences': evaluation['num_sentences'],
                    'num_tokens': evaluation['num_tokens'],
                    'avg_sentence_length': evaluation['avg_sentence_length'],
                    'ai_detection_label': evaluation['ai_detection_label'],
                    'ai_detection_score': evaluation['ai_detection_score'],
                    'ai_evaluated': True,
                    'evaluated_at': datetime.now()
                }
            }
        )
        
        return jsonify({
            'message': 'Essay evaluated successfully',
            'evaluation': evaluation
        }), 200
        
    except Exception as e:
        print(f"Error evaluating essay: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/essays/<essay_id>/statements', methods=['GET', 'OPTIONS'])
def get_essay_statements(essay_id):
    """Get atomic statements for an essay"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    try:
        # Optional authentication (allows public posts to be viewed)
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_id = verify_token(token)
        
        # Validate essay_id format
        if not ObjectId.is_valid(essay_id):
            return jsonify({'error': 'Invalid essay ID format'}), 400
        
        # ✅ Use model method instead of direct query
        essay = essay_model.get_by_id(essay_id)
        if not essay:
            return jsonify({'error': 'Essay not found'}), 404
        
        # Check access permissions (same logic as essay viewing)
        if user_id != essay.get('user_id'):
            # Check if essay is shared as public post
            post = mongo.db.posts.find_one({'essay_id': essay_id})
            if not post or post.get('visibility') != 'public':
                return jsonify({'error': 'Unauthorized'}), 403
        
        # ✅ Use model method to check if statements exist
        if essay_model.has_statements(essay_id):
            print(f"📦 Returning cached statements for essay {essay_id}")
            statements_data = essay_model.get_statements(essay_id)
            return jsonify({
                'statements': statements_data['statements'],
                'summary': statements_data['summary'],
                'cached': True
            }), 200
        
        # Extract statements using LLM
        print(f"🔬 Extracting new statements for essay {essay_id}")
        content = essay.get('content', '')
        
        if not content:
            return jsonify({'error': 'Essay has no content'}), 400
        
        result = llm_service.extract_atomic_statements(content)
        
        # ✅ Use model method to save statements
        essay_model.add_statements(
            essay_id,
            result['statements'],
            result['summary']
        )
        
        return jsonify({
            'statements': result['statements'],
            'summary': result['summary'],
            'cached': False
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting statements: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/essays/<essay_id>/statements/regenerate', methods=['POST', 'OPTIONS'])
def regenerate_statements(essay_id):
    """Force regeneration of statements (requires authentication)"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    # Require authentication for regeneration
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authentication required'}), 401
    
    token = auth_header.split(' ')[1]
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    try:
        # Validate essay_id format
        if not ObjectId.is_valid(essay_id):
            return jsonify({'error': 'Invalid essay ID'}), 400
        
        # ✅ Use model method
        essay = essay_model.get_by_id(essay_id)
        if not essay:
            return jsonify({'error': 'Essay not found'}), 404
        
        # Check ownership
        if essay['user_id'] != user_id:
            return jsonify({'error': 'Unauthorized - not your essay'}), 403
        
        # Extract statements
        content = essay.get('content', '')
        if not content:
            return jsonify({'error': 'Essay has no content'}), 400
        
        print(f"🔄 Regenerating statements for essay {essay_id}")
        result = llm_service.extract_atomic_statements(content)
        
        # ✅ Use model method to update statements
        essay_model.regenerate_statements(
            essay_id,
            result['statements'],
            result['summary']
        )
        
        return jsonify({
            'statements': result['statements'],
            'summary': result['summary'],
            'message': 'Statements regenerated successfully'
        }), 200
        
    except Exception as e:
        print(f"❌ Error regenerating statements: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500