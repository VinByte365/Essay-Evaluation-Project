from flask import Blueprint, request, jsonify
from ..extensions import mongo, nlp, detector_pipe
import language_tool_python
from docx import Document

api_bp = Blueprint('api', __name__)
tool = language_tool_python.LanguageTool('en-US')

def extract_text_from_docx(file_stream):
    doc = Document(file_stream)
    return "\n".join([para.text for para in doc.paragraphs])

@api_bp.route('/upload-essay', methods=['POST'])
def upload_essay():
    # 1. Read file from request
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # 2. Extract text based on file type
    if file.filename.endswith('.txt'):
        text = file.read().decode('utf-8')
    elif file.filename.endswith('.docx'):
        text = extract_text_from_docx(file.stream)
    else:
        return jsonify({'error': 'Unsupported file type'}), 400
    
    # 3. NLP Analysis (spaCy)
    doc = nlp(text)
    
    # 4. Grammar Check (LanguageTool)
    matches = tool.check(text)
    total_errors = len(matches)
    error_feedback = []
    for match in matches[:10]:  # Limit feedback to first 10 errors
        error_feedback.append({
            'message': match.message,
            'context': match.context,
            'replacements': match.replacements
        })

    # 5. Linguistic Stats
    num_sentences = len(list(doc.sents))
    num_tokens = len(doc)
    num_entities = len(doc.ents)
    avg_sentence_length = num_tokens / max(num_sentences, 1)

    # 6. Simple scoring - you can refine this as needed
    score = max(0, 100 - total_errors * 2)

    # 7. AI-generated text detection (using HuggingFace pipeline)
    ai_result = detector_pipe(text)
    ai_label = ai_result[0]['label']
    ai_score = ai_result[0]['score']

    # 8. Compose merged result
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

    # Optionally, save to database
    # mongo.db.essays.insert_one({'text': text, 'result': result})

    return jsonify(result), 200
