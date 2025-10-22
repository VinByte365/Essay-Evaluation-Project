from flask import Blueprint, request, jsonify
from ..extensions import mongo, nlp
import language_tool_python
from docx import Document
import io

api_bp = Blueprint('api', __name__)
tool = language_tool_python.LanguageTool('en-US')

def extract_text_from_docx(file_stream):
    doc = Document(file_stream)
    return "\n".join([para.text for para in doc.paragraphs])

@api_bp.route('/upload-essay', methods=['POST'])
def upload_essay():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Read file content based on file extension
    if file.filename.endswith('.txt'):
        text = file.read().decode('utf-8')
    elif file.filename.endswith('.docx'):
        # Use python-docx to parse .docx files
        text = extract_text_from_docx(file.stream)
    else:
        return jsonify({'error': 'Unsupported file type'}), 400
    
    # Run NLP analysis
    doc = nlp(text)

    # LanguageTool grammar check
    matches = tool.check(text)
    total_errors = len(matches)
    # Extract grammar error descriptions for feedback
    error_feedback = []
    for match in matches[:10]:  # limit feedback to first 10 errors
        error_feedback.append({
            'message': match.message,
            'context': match.context,
            'replacements': match.replacements
        })

    # Basic linguistic stats
    num_sentences = len(list(doc.sents))
    num_tokens = len(doc)
    num_entities = len(doc.ents)
    
    # Example complexity metric: average sentence length
    avg_sentence_length = num_tokens / max(num_sentences, 1)
    
    # Simple scoring example: higher errors reduce score
    score = max(0, 100 - total_errors * 2)
    
    # Form result
    result = {
        'score': score,
        'total_grammar_errors': total_errors,
        'error_feedback': error_feedback,
        'num_sentences': num_sentences,
        'num_tokens': num_tokens,
        'num_entities': num_entities,
        'avg_sentence_length': avg_sentence_length
    }
    
    # Optionally, save to MongoDB if you want
    # mongo.db.essays.insert_one({'text': text, 'result': result})

    return jsonify(result), 200
