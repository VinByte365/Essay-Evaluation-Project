from flask import Blueprint, request, jsonify
from ..extensions import mongo, nlp, detector_pipe
import language_tool_python
from docx import Document
import io
import traceback

api_bp = Blueprint('api', __name__)
tool = language_tool_python.LanguageTool('en-US')


def extract_text_from_docx(file_stream):
    """Extract text from .docx file with error handling"""
    try:
        # Reset stream position to beginning
        file_stream.seek(0)
        doc = Document(file_stream)
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        
        if not text or len(text.strip()) < 10:
            raise ValueError("Document appears to be empty or too short")
        
        return text
    except Exception as e:
        raise ValueError(f"Failed to extract text from .docx file: {str(e)}")


@api_bp.route('/upload-essay', methods=['POST', 'OPTIONS'])
def upload_essay():
    # Handle preflight request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        # 1. Validate file exists
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # 2. Extract text based on file type
        try:
            if file.filename.endswith('.txt'):
                text = file.read().decode('utf-8')
            elif file.filename.endswith('.docx'):
                text = extract_text_from_docx(file.stream)
            else:
                return jsonify({'error': 'Unsupported file type. Only .txt and .docx allowed'}), 400
        except Exception as e:
            return jsonify({'error': f'File processing error: {str(e)}'}), 400
        
        # Validate text length
        if not text or len(text.strip()) < 10:
            return jsonify({'error': 'Text is too short (minimum 10 characters)'}), 400
        
        # 3. NLP Analysis (spaCy)
        doc = nlp(text)
        
        # 4. Grammar Check (LanguageTool)
        matches = tool.check(text)
        total_errors = len(matches)
        error_feedback = []
        for match in matches[:10]:  # Limit to first 10 errors
            error_feedback.append({
                'message': match.message,
                'context': match.context,
                'replacements': match.replacements[:5]  # Limit replacements
            })

        # 5. Linguistic Stats
        num_sentences = len(list(doc.sents))
        num_tokens = len(doc)
        num_entities = len(doc.ents)
        avg_sentence_length = num_tokens / max(num_sentences, 1)

        # 6. Simple scoring
        score = max(0, 100 - total_errors * 2)

        # 7. AI-generated text detection
        try:
            # Limit text length for AI detector (many models have token limits)
            text_for_ai = text[:512]
            ai_result = detector_pipe(text_for_ai)
            ai_label = ai_result[0]['label']
            ai_score = ai_result[0]['score']
        except Exception as e:
            print(f"AI detection error: {str(e)}")
            ai_label = "Error"
            ai_score = 0.0

        # 8. Compose result
        result = {
            'score': score,
            'total_grammar_errors': total_errors,
            'error_feedback': error_feedback,
            'num_sentences': num_sentences,
            'num_tokens': num_tokens,
            'num_entities': num_entities,
            'avg_sentence_length': avg_sentence_length,
            'ai_detection_label': ai_label,
            'ai_detection_score': ai_score
        }

        return jsonify(result), 200
        
    except Exception as e:
        # Log the full error for debugging
        print(f"Unexpected error in upload_essay: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500
