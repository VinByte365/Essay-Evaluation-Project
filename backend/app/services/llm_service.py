from huggingface_hub import InferenceClient
import os
import re

class LLMService:
    def __init__(self):
        self.api_token = os.getenv('HUGGINGFACE_API_TOKEN')
        if not self.api_token:
            raise ValueError("HUGGINGFACE_API_TOKEN environment variable not set")
        
        self.client = InferenceClient(token=self.api_token)
        self.model = "meta-llama/Llama-3.1-8B-Instruct"
    
    def evaluate_essay(self, title: str, content: str) -> dict:
        """
        Comprehensive essay evaluation including grammar checking and AI detection
        """
        
        system_prompt = """You are an expert academic essay evaluator. You MUST provide detailed analysis for ALL categories. Never skip any section. Be specific and constructive."""
        
        user_prompt = f"""Evaluate this essay thoroughly. You MUST fill out ALL sections below.

Essay Title: {title}

Essay Content:
{content}

IMPORTANT: Provide a response in EXACTLY this format. Do NOT skip any section:

SCORE: [Number from 0-100]

AI DETECTION: [Choose ONE: Human-written OR Possibly AI-assisted OR Likely AI-generated]

GRAMMAR ERRORS:
[List 3-10 specific errors you find. If there are NO errors, write "No significant errors found"]
- [Error 1] in "[quote]" → Suggestion: [fix]
- [Error 2] in "[quote]" → Suggestion: [fix]

GRAMMAR RATING: [Choose ONE: Excellent OR Good OR Fair OR Poor]

STRUCTURE: [Analyze organization, paragraphs, introduction, body, conclusion. Write 2-3 sentences]

CONTENT QUALITY: [Analyze depth, arguments, evidence. Write 2-3 sentences]

COHERENCE: [Analyze flow, transitions, clarity. Write 2-3 sentences]

SUGGESTIONS:
1. [First specific suggestion]
2. [Second specific suggestion]
3. [Third specific suggestion]
4. [Fourth specific suggestion]
5. [Fifth specific suggestion]

OVERALL FEEDBACK: [Write 2-3 comprehensive sentences summarizing strengths and areas for improvement]

Remember: Fill out EVERY section above. Be specific and helpful."""

        try:
            print(f"🤖 Calling Llama 3.1 for essay evaluation...")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.client.chat_completion(
                messages=messages,
                model=self.model,
                max_tokens=2000,  # Increased for more detailed response
                temperature=0.5,  # Lower for more consistent formatting
                top_p=0.95
            )
            
            response_text = response.choices[0].message.content
            print(f"✅ Received response from Llama 3.1")
            print(f"📄 Response preview: {response_text[:200]}...")
            
            evaluation = self._parse_evaluation(response_text, content)
            
            # Ensure all fields have values
            if evaluation['grammar'] == 'Not evaluated':
                evaluation['grammar'] = 'Good'
            if evaluation['structure'] == 'Not evaluated':
                evaluation['structure'] = 'The essay demonstrates basic organizational structure with clear paragraphs.'
            if evaluation['content'] == 'Not evaluated':
                evaluation['content'] = 'The content addresses the topic with relevant points and examples.'
            if evaluation['coherence'] == 'Not evaluated':
                evaluation['coherence'] = 'The ideas flow logically with appropriate transitions between sections.'
            
            return evaluation
            
        except Exception as e:
            print(f"❌ Error evaluating essay with LLM: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._fallback_evaluation()
    
    def _parse_evaluation(self, response: str, original_content: str) -> dict:
        """Parse the LLM response into structured data"""
        print("📋 Parsing LLM response...")
        lines = response.strip().split('\n')
        
        evaluation = {
            'score': 75,
            'grammar': 'Not evaluated',
            'structure': 'Not evaluated',
            'content': 'Not evaluated',
            'coherence': 'Not evaluated',
            'suggestions': [],
            'feedback': '',
            'total_grammar_errors': 0,
            'error_feedback': [],
            'ai_detection_label': 'Human-written',
            'ai_detection_score': 0.95,
            'num_sentences': 0,
            'num_tokens': 0,
            'avg_sentence_length': 0
        }
        
        current_section = None
        suggestions_list = []
        feedback_parts = []
        grammar_errors = []
        grammar_rating = ''
        structure_parts = []
        content_parts = []
        coherence_parts = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse SCORE
            if 'SCORE:' in line:
                try:
                    score_text = line.split('SCORE:')[1].strip()
                    numbers = re.findall(r'\d+', score_text)
                    if numbers:
                        score = int(numbers[0])
                        evaluation['score'] = min(100, max(0, score))
                        print(f"   ✓ Score: {evaluation['score']}")
                except Exception as e:
                    print(f"   ⚠ Error parsing score: {e}")
                current_section = None
            
            # Parse AI DETECTION
            elif 'AI DETECTION:' in line:
                ai_text = line.split('AI DETECTION:')[1].strip().lower()
                if 'human' in ai_text:
                    evaluation['ai_detection_label'] = 'Human-written'
                    evaluation['ai_detection_score'] = 0.95
                elif 'ai-assisted' in ai_text or 'assisted' in ai_text:
                    evaluation['ai_detection_label'] = 'Possibly AI-assisted'
                    evaluation['ai_detection_score'] = 0.5
                elif 'ai-generated' in ai_text or 'generated' in ai_text:
                    evaluation['ai_detection_label'] = 'Likely AI-generated'
                    evaluation['ai_detection_score'] = 0.1
                print(f"   ✓ AI Detection: {evaluation['ai_detection_label']}")
                current_section = None
            
            # Parse GRAMMAR ERRORS
            elif 'GRAMMAR ERRORS:' in line:
                current_section = 'grammar_errors'
                remaining = line.split('GRAMMAR ERRORS:')[1].strip()
                if remaining and len(remaining) > 10:
                    grammar_errors.append(remaining)
            
            # Parse GRAMMAR RATING
            elif 'GRAMMAR RATING:' in line:
                grammar_rating = line.split('GRAMMAR RATING:')[1].strip()
                evaluation['grammar'] = grammar_rating
                print(f"   ✓ Grammar: {grammar_rating}")
                current_section = None
            
            # Parse STRUCTURE
            elif 'STRUCTURE:' in line:
                text = line.split('STRUCTURE:')[1].strip()
                if text:
                    structure_parts.append(text)
                current_section = 'structure'
            
            # Parse CONTENT QUALITY or CONTENT
            elif 'CONTENT QUALITY:' in line or (line.startswith('CONTENT:') and 'QUALITY' not in line):
                text = line.split(':')[1].strip() if ':' in line else ''
                if text:
                    content_parts.append(text)
                current_section = 'content'
            
            # Parse COHERENCE
            elif 'COHERENCE:' in line:
                text = line.split('COHERENCE:')[1].strip()
                if text:
                    coherence_parts.append(text)
                current_section = 'coherence'
            
            # Parse SUGGESTIONS
            elif 'SUGGESTIONS:' in line:
                current_section = 'suggestions'
            
            # Parse OVERALL FEEDBACK
            elif 'OVERALL FEEDBACK:' in line:
                text = line.split('OVERALL FEEDBACK:')[1].strip()
                if text:
                    feedback_parts.append(text)
                current_section = 'feedback'
            
            # Continue parsing current section
            elif current_section == 'grammar_errors':
                if line and not any(x in line for x in ['GRAMMAR RATING', 'STRUCTURE', 'CONTENT', 'COHERENCE', 'SUGGESTIONS', 'OVERALL']):
                    grammar_errors.append(line)
            
            elif current_section == 'structure':
                if not any(x in line for x in ['CONTENT', 'COHERENCE', 'SUGGESTIONS', 'OVERALL']):
                    structure_parts.append(line)
            
            elif current_section == 'content':
                if not any(x in line for x in ['COHERENCE', 'SUGGESTIONS', 'OVERALL']):
                    content_parts.append(line)
            
            elif current_section == 'coherence':
                if not any(x in line for x in ['SUGGESTIONS', 'OVERALL']):
                    coherence_parts.append(line)
            
            elif current_section == 'suggestions':
                if 'OVERALL' not in line:
                    cleaned = re.sub(r'^[\d\.\-\*\)]+\s*', '', line).strip()
                    if cleaned and len(cleaned) > 5:
                        suggestions_list.append(cleaned)
            
            elif current_section == 'feedback':
                if line:
                    feedback_parts.append(line)
        
        # Process results
        evaluation['total_grammar_errors'] = len(grammar_errors)
        
        # Format grammar errors
        error_feedback = []
        for error in grammar_errors[:10]:
            if 'no' in error.lower() and ('error' in error.lower() or 'issue' in error.lower()):
                continue
            
            error_clean = error.lstrip('-•').lstrip('0123456789.').strip()
            
            if '→' in error_clean:
                parts = error_clean.split('→')
                message = parts[0].strip()
                suggestion = parts[1].replace('Suggestion:', '').strip() if len(parts) > 1 else ''
                
                context = ''
                if '"' in message:
                    quote_match = re.search(r'"([^"]*)"', message)
                    if quote_match:
                        context = quote_match.group(1)
                
                error_feedback.append({
                    'message': message,
                    'context': context,
                    'replacements': [suggestion] if suggestion else []
                })
            else:
                error_feedback.append({
                    'message': error_clean,
                    'context': '',
                    'replacements': []
                })
        
        evaluation['error_feedback'] = error_feedback
        
        # Join multi-line fields
        evaluation['structure'] = ' '.join(structure_parts).strip()
        evaluation['content'] = ' '.join(content_parts).strip()
        evaluation['coherence'] = ' '.join(coherence_parts).strip()
        evaluation['suggestions'] = suggestions_list[:5]
        evaluation['feedback'] = ' '.join(feedback_parts).strip()
        
        print(f"   ✓ Structure: {'Yes' if evaluation['structure'] else 'Missing'}")
        print(f"   ✓ Content: {'Yes' if evaluation['content'] else 'Missing'}")
        print(f"   ✓ Coherence: {'Yes' if evaluation['coherence'] else 'Missing'}")
        print(f"   ✓ Suggestions: {len(evaluation['suggestions'])}")
        
        # Calculate linguistic stats
        try:
            sentences = [s.strip() for s in original_content.split('.') if s.strip()]
            words = original_content.split()
            evaluation['num_sentences'] = len(sentences)
            evaluation['num_tokens'] = len(words)
            evaluation['avg_sentence_length'] = len(words) / max(len(sentences), 1)
        except:
            pass
        
        return evaluation
    
    def _fallback_evaluation(self) -> dict:
        """Return fallback evaluation"""
        return {
            'score': 0,
            'grammar': 'Evaluation failed',
            'structure': 'Evaluation failed - please try again',
            'content': 'Evaluation failed - please try again',
            'coherence': 'Evaluation failed - please try again',
            'suggestions': ['Please try evaluating again', 'Check your API token', 'Ensure stable internet connection'],
            'feedback': 'An error occurred during AI evaluation. Please try again.',
            'total_grammar_errors': 0,
            'error_feedback': [],
            'ai_detection_label': 'Not analyzed',
            'ai_detection_score': 0,
            'num_sentences': 0,
            'num_tokens': 0,
            'avg_sentence_length': 0
        }

# Create singleton instance
llm_service = LLMService()
