from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import spacy
import language_tool_python
from app.models.essay import Essay
from bson import ObjectId

api_bp = Blueprint('api', __name__)

# Initialize NLP tools
nlp = spacy.load("en_core_web_sm")
tool = language_tool_python.LanguageTool('en-US')

# Initialize MongoDB (assuming you have db connection)
from app import mongo  # Import your MongoDB connection
essay_model = Essay(mongo.db)

@api_bp.route('/upload-essay', methods=['POST', 'OPTIONS'])
def upload_essay():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        # 1. Validate file
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Get user ID from session/auth (for now, use a test user)
        user_id = request.headers.get('X-User-Id', 'test_user')
        
        # 2. Extract text
        if file.filename.endswith('.txt'):
            text = file.read().decode('utf-8')
        elif file.filename.endswith('.docx'):
            text = extract_text_from_docx(file.stream)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        if not text or len(text.strip()) < 10:
            return jsonify({'error': 'Text is too short'}), 400
        
        # Get title from filename
        title = file.filename.rsplit('.', 1)[0]
        
        # 3. Create essay record in DB with "evaluating" status
        essay = essay_model.create(
            user_id=user_id,
            title=title,
            content=text[:500],  # Store preview
            file_name=secure_filename(file.filename)
        )
        
        essay_id = essay['_id']
        
        # 4. Perform NLP analysis
        doc = nlp(text)
        matches = tool.check(text)
        
        # Grammar errors
        total_errors = len(matches)
        error_feedback = []
        for match in matches[:10]:
            error_feedback.append({
                'message': match.message,
                'context': match.context,
                'replacements': match.replacements[:5]
            })
        
        # Linguistic stats
        num_sentences = len(list(doc.sents))
        num_tokens = len(doc)
        num_entities = len(doc.ents)
        avg_sentence_length = num_tokens / max(num_sentences, 1)
        
        # Simple scoring
        score = max(0, 100 - total_errors * 2)
        
        # AI detection (placeholder)
        ai_label = "Human-written"
        ai_score = 0.95
        
        # 5. Prepare evaluation results
        evaluation_results = {
            'score': score,
            'total_grammar_errors': total_errors,
            'error_feedback': error_feedback,
            'num_sentences': num_sentences,
            'num_tokens': num_tokens,
            'num_entities': num_entities,
            'avg_sentence_length': avg_sentence_length,
            'ai_detection_label': ai_label,
            'ai_detection_score': ai_score,
            'feedback': f"Found {total_errors} grammar errors. " + 
                       (error_feedback[0]['message'] if error_feedback else "Good job!")
        }
        
        # 6. Update essay with evaluation results
        updated_essay = essay_model.update_evaluation(essay_id, evaluation_results)
        
        # 7. Return results with essay ID
        result = {
            'essay_id': essay_id,
            **evaluation_results
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/essays', methods=['GET', 'OPTIONS'])
def get_essays():
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
    user_id = verify_token(token)  # ← Use JWT verification
    
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    essays = essay_model.get_by_user(user_id)
    return jsonify({'essays': essays}), 200



@api_bp.route('/essays/<essay_id>', methods=['GET'])
def get_essay(essay_id):
    """Get a specific essay"""
    try:
        essay = essay_model.get_by_id(essay_id)
        if not essay:
            return jsonify({'error': 'Essay not found'}), 404
        return jsonify(essay), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/essays/<essay_id>', methods=['DELETE'])
def delete_essay(essay_id):
    """Delete an essay"""
    try:
        essay_model.delete(essay_id)
        return jsonify({'message': 'Essay deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
