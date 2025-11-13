from huggingface_hub import InferenceClient
import os
import re

# Try to import spaCy (optional - will use fallback if not available)
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except:
    SPACY_AVAILABLE = False
    print("⚠️ spaCy not available - using basic sentence splitting")


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


Remember: Fill out EVERY section above. Be specific and helpful. Return those data BASED on the language used in the uploaded essay"""


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
    
    # ═══════════════════════════════════════════════════════════════════
    # ✅ NEW: ATOMIC STATEMENT EXTRACTION (Added below)
    # ═══════════════════════════════════════════════════════════════════
    
    def extract_atomic_statements(self, essay_content: str) -> dict:
        """
        Extract atomic statements from essay using LLM
        Returns: {'statements': [...], 'summary': {...}}
        """
        print(f"🔬 Extracting atomic statements...")
        
        try:
            # Step 1: Split into sentences (basic or spaCy)
            raw_statements = self._segment_sentences(essay_content)
            
            # Step 2: Use LLM for classification
            enhanced_statements = self._llm_classify_statements(raw_statements)
            
            # Step 3: Generate summary
            summary = self._generate_statement_summary(enhanced_statements)
            
            print(f"✅ Extracted {len(enhanced_statements)} statements")
            
            return {
                'statements': enhanced_statements,
                'summary': summary
            }
            
        except Exception as e:
            print(f"❌ Error extracting statements: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'statements': [], 'summary': {}}
    
    def _segment_sentences(self, text: str) -> list:
        """Split text into sentences"""
        statements = []
        
        if SPACY_AVAILABLE:
            # Use spaCy for better sentence segmentation
            doc = nlp(text)
            for idx, sent in enumerate(doc.sents):
                if len(sent.text.split()) >= 3:
                    statements.append({
                        'id': f'stmt_{idx}',
                        'text': sent.text.strip(),
                        'position': {
                            'start': sent.start_char,
                            'end': sent.end_char,
                            'sentence_index': idx
                        },
                        'word_count': len(sent.text.split()),
                        'has_citation': self._has_citation(sent.text),
                        'entities': [{'text': ent.text, 'label': ent.label_} for ent in sent.ents]
                    })
        else:
            # Fallback: basic sentence splitting
            sentences = re.split(r'[.!?]+', text)
            for idx, sent in enumerate(sentences):
                sent = sent.strip()
                if len(sent.split()) >= 3:
                    statements.append({
                        'id': f'stmt_{idx}',
                        'text': sent,
                        'position': {
                            'start': text.find(sent),
                            'end': text.find(sent) + len(sent),
                            'sentence_index': idx
                        },
                        'word_count': len(sent.split()),
                        'has_citation': self._has_citation(sent),
                        'entities': []
                    })
        
        return statements
    
    def _llm_classify_statements(self, statements: list) -> list:
        """Use LLM to classify statement types and strength"""
        
        if not statements:
            return []
        
        # Prepare statement list for LLM
        statements_text = "\n".join([
            f"{i+1}. {stmt['text'][:150]}" 
            for i, stmt in enumerate(statements)
        ])
        
        system_prompt = """You are an expert in academic argument analysis. Classify each statement."""
        
        user_prompt = f"""Analyze these {len(statements)} statements from an academic essay.

For EACH statement, provide:
- Type: claim, evidence, transition, or conclusion
- Strength: 0.0 to 1.0

Statements:
{statements_text}

Respond EXACTLY in this format (one per line):
1: type=claim | strength=0.8
2: type=evidence | strength=0.9
3: type=transition | strength=0.6

Continue for all {len(statements)} statements."""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.client.chat_completion(
                messages=messages,
                model=self.model,
                max_tokens=800,
                temperature=0.3
            )
            
            analysis_text = response.choices[0].message.content
            
            # Parse LLM response
            for i, stmt in enumerate(statements):
                pattern = rf"{i+1}:\s*type=(\w+)\s*\|\s*strength=([\d\.]+)"
                match = re.search(pattern, analysis_text, re.IGNORECASE)
                
                if match:
                    stmt['type'] = match.group(1).lower()
                    stmt['strength'] = float(match.group(2))
                else:
                    # Fallback classification
                    stmt['type'] = self._simple_classify(stmt['text'])
                    stmt['strength'] = 0.5
                
                stmt['complexity'] = self._calculate_complexity(stmt['text'])
            
            # Analyze relationships
            statements = self._analyze_relationships(statements)
            
            return statements
            
        except Exception as e:
            print(f"⚠️ LLM classification failed: {e}")
            # Use fallback
            for stmt in statements:
                stmt['type'] = self._simple_classify(stmt['text'])
                stmt['strength'] = 0.5
                stmt['complexity'] = self._calculate_complexity(stmt['text'])
            return statements
    
    def _simple_classify(self, text: str) -> str:
        """Rule-based statement classification"""
        text_lower = text.lower()
        
        if any(w in text_lower for w in ['therefore', 'thus', 'in conclusion', 'hence']):
            return 'conclusion'
        if any(w in text_lower for w in ['according to', 'research shows', 'study']):
            return 'evidence'
        if any(w in text_lower for w in ['however', 'moreover', 'furthermore']):
            return 'transition'
        return 'claim'
    
    def _has_citation(self, text: str) -> bool:
        """Check for citation markers"""
        patterns = [r'\(\d{4}\)', r'\[\d+\]', r'\(.*?et al.*?\)']
        return any(re.search(p, text) for p in patterns)
    
    def _calculate_complexity(self, text: str) -> float:
        """Calculate text complexity score"""
        words = text.split()
        if not words:
            return 0.0
        word_count = len(words)
        avg_word_len = sum(len(w) for w in words) / word_count
        complexity = min(1.0, (word_count / 30.0) + (avg_word_len / 20.0))
        return round(complexity, 2)
    
    def _analyze_relationships(self, statements: list) -> list:
        """Find relationships between statements"""
        for i, stmt in enumerate(statements):
            linked = []
            
            # Link to previous if contains discourse marker
            if i > 0:
                markers = ['therefore', 'however', 'this', 'thus']
                if any(m in stmt['text'].lower() for m in markers):
                    linked.append(f"stmt_{i-1}")
            
            # Link if shares entities (only if spaCy available)
            if SPACY_AVAILABLE and i < len(statements) - 1:
                curr_ents = set(e['text'] for e in stmt.get('entities', []))
                for j in range(i + 1, min(i + 3, len(statements))):
                    next_ents = set(e['text'] for e in statements[j].get('entities', []))
                    if curr_ents & next_ents:
                        linked.append(f"stmt_{j}")
            
            stmt['linked_to'] = linked
        
        return statements
    
    def _generate_statement_summary(self, statements: list) -> dict:
        """Generate summary statistics"""
        if not statements:
            return {}
        
        type_counts = {}
        for stmt in statements:
            t = stmt.get('type', 'unknown')
            type_counts[t] = type_counts.get(t, 0) + 1
        
        avg_strength = sum(stmt.get('strength', 0.5) for stmt in statements) / len(statements)
        avg_complexity = sum(stmt.get('complexity', 0.5) for stmt in statements) / len(statements)
        cited = sum(1 for stmt in statements if stmt.get('has_citation', False))
        
        return {
            'total_statements': len(statements),
            'by_type': type_counts,
            'average_strength': round(avg_strength, 2),
            'average_complexity': round(avg_complexity, 2),
            'citations_count': cited,
            'citation_rate': round(cited / len(statements), 2) if statements else 0
        }


# Create singleton instance
llm_service = LLMService()
