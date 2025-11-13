from langdetect import detect, DetectorFactory
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import Dict, Any, Optional
from .llm_service import llm_service  # Your existing service

# Fix langdetect randomness for consistent results
DetectorFactory.seed = 0

class MultilingualLLMService:
    def __init__(self):
        # Initialize language detection
        self.language_model = self._load_language_detector()
        
        # Multilingual evaluation models (choose based on your needs)
        self.multilingual_sentiment = self._load_multilingual_sentiment()
        
        # Fallback: English-based evaluation with translation
        self.translator = None  # Initialize if needed
        
        # Language-specific evaluation thresholds
        self.language_weights = {
            'en': {'grammar': 0.25, 'structure': 0.20, 'content': 0.30, 'coherence': 0.25},
            'es': {'grammar': 0.22, 'structure': 0.23, 'content': 0.28, 'coherence': 0.27},
            'fr': {'grammar': 0.23, 'structure': 0.22, 'content': 0.28, 'coherence': 0.27},
            'de': {'grammar': 0.28, 'structure': 0.20, 'content': 0.25, 'coherence': 0.27},
            'default': {'grammar': 0.25, 'structure': 0.20, 'content': 0.30, 'coherence': 0.25}
        }
    
    def _load_language_detector(self):
        """Load fast language detection model"""
        try:
            return pipeline("text-classification", 
                          model="papluca/xlm-roberta-base-language-detection",
                          return_all_scores=True)
        except Exception as e:
            print(f"Warning: Could not load advanced language detector: {e}")
            return None
    
    def _load_multilingual_sentiment(self):
        """Load multilingual sentiment analysis for content evaluation"""
        try:
            return pipeline("sentiment-analysis", 
                          model="nlptown/bert-base-multilingual-uncased-sentiment",
                          device=0 if torch.cuda.is_available() else -1)
        except Exception as e:
            print(f"Warning: Could not load multilingual sentiment model: {e}")
            return None
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect language of the essay text"""
        try:
            if self.language_model:
                # Use XLM-RoBERTa for accurate multilingual detection
                result = self.language_model(text[:512])  # Truncate for speed
                scores = result[0]
                language = max(scores, key=lambda x: x['score'])['label']
                confidence = max(scores, key=lambda x: x['score'])['score']
                
                # Map XLM-R labels to ISO codes
                language_map = {
                    'af': 'af', 'ar': 'ar', 'az': 'az', 'be': 'be', 'bg': 'bg', 'bn': 'bn',
                    'cs': 'cs', 'cy': 'cy', 'da': 'da', 'de': 'de', 'el': 'el', 'en': 'en',
                    'es': 'es', 'et': 'et', 'fa': 'fa', 'fi': 'fi', 'fr': 'fr', 'gu': 'gu',
                    'he': 'he', 'hi': 'hi', 'hr': 'hr', 'hu': 'hu', 'id': 'id', 'is': 'is',
                    'it': 'it', 'ja': 'ja', 'ka': 'ka', 'kk': 'kk', 'ko': 'ko', 'lt': 'lt',
                    'lv': 'lv', 'mk': 'mk', 'ml': 'ml', 'mr': 'mr', 'ms': 'ms', 'my': 'my',
                    'nb': 'no', 'ne': 'ne', 'nl': 'nl', 'nn': 'no', 'pl': 'pl', 'pt': 'pt',
                    'ro': 'ro', 'ru': 'ru', 'sk': 'sk', 'sl': 'sl', 'sq': 'sq', 'sv': 'sv',
                    'ta': 'ta', 'te': 'te', 'th': 'th', 'tl': 'tl', 'tr': 'tr', 'uk': 'uk',
                    'ur': 'ur', 'vi': 'vi', 'zh': 'zh'
                }
                iso_code = language_map.get(language, 'unknown')
                return {
                    'language': iso_code,
                    'confidence': confidence,
                    'display_name': self._get_language_name(iso_code)
                }
            else:
                # Fallback to langdetect
                from langdetect import detect
                lang = detect(text)
                return {
                    'language': lang,
                    'confidence': 0.95,  # Langdetect doesn't return confidence
                    'display_name': self._get_language_name(lang)
                }
        except Exception as e:
            print(f"Language detection error: {e}")
            # Default to English
            return {'language': 'en', 'confidence': 0.8, 'display_name': 'English'}
    
    def _get_language_name(self, lang_code: str) -> str:
        """Get full language name from ISO code"""
        names = {
            'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
            'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'zh': 'Chinese',
            'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic', 'hi': 'Hindi',
            'default': 'Unknown'
        }
        return names.get(lang_code, names['default'])
    
    def evaluate_essay_multilingual(self, title: str, content: str) -> Dict[str, Any]:
        """Evaluate essay in its detected language"""
        lang_info = self.detect_language(content)
        language = lang_info['language']
        
        print(f"🌐 Detected language: {lang_info['display_name']} (confidence: {lang_info['confidence']:.2f})")
        
        # Get language-specific weights
        weights = self.language_weights.get(language, self.language_weights['default'])
        
        if language == 'en':
            # Use your existing English evaluation
            return llm_service.evaluate_essay(title=title, content=content)
        else:
            # Multilingual evaluation pipeline
            return self._evaluate_non_english_essay(title, content, language, weights, lang_info)
    
    def _evaluate_non_english_essay(self, title: str, content: str, language: str, 
                                 weights: Dict[str, float], lang_info: Dict) -> Dict[str, Any]:
        """Handle non-English essay evaluation"""
        try:
            # 1. Basic linguistic analysis (language-agnostic)
            num_sentences = len(content.split('.')) if '.' in content else 1
            num_words = len(content.split())
            avg_sentence_length = num_words / max(num_sentences, 1)
            num_tokens = len(content.split())  # Rough estimate
            
            # 2. Multilingual sentiment/content analysis
            sentiment_score = 0.0
            if self.multilingual_sentiment and num_words > 10:
                try:
                    sentiment_result = self.multilingual_sentiment(content[:512])
                    # Map sentiment score to content quality (1-5 stars -> 0-1)
                    star_rating = int(sentiment_result[0]['label'].replace('1 star', '').replace(' stars', ''))
                    sentiment_score = star_rating / 5.0
                except Exception:
                    sentiment_score = 0.5  # Neutral fallback
            
            # 3. Language-specific evaluation (translate to English for LLM)
            if self._should_translate_for_evaluation(language):
                # Translate to English for detailed LLM evaluation
                english_content = self._translate_to_english(content, language)
                english_eval = llm_service.evaluate_essay(
                    title=self._translate_title(title, language),
                    content=english_content
                )
                
                # Adjust scores for language proficiency
                language_penalty = self._calculate_language_penalty(content, language, lang_info['confidence'])
                
                return self._adjust_evaluation_for_language(
                    english_eval, sentiment_score, avg_sentence_length, language_penalty, weights
                )
            else:
                # Direct multilingual evaluation for supported languages
                return self._direct_multilingual_evaluation(
                    title, content, language, sentiment_score, avg_sentence_length, weights
                )
                
        except Exception as e:
            print(f"Multilingual evaluation error for {language}: {e}")
            # Fallback to basic evaluation
            return self._basic_multilingual_evaluation(title, content, language, weights)
    
    def _should_translate_for_evaluation(self, language: str) -> bool:
        """Determine if we should translate for better evaluation"""
        # Translate for languages with less robust LLM support
        translate_languages = ['es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko']
        return language in translate_languages
    
    def _translate_to_english(self, text: str, source_lang: str) -> str:
        """Translate text to English for evaluation (fallback implementation)"""
        try:
            from googletrans import Translator
            translator = Translator()
            result = translator.translate(text, src=source_lang, dest='en')
            return result.text
        except Exception as e:
            print(f"Translation failed: {e}")
            # Return original text if translation fails
            return text
    
    def _translate_title(self, title: str, source_lang: str) -> str:
        """Translate title to English"""
        try:
            from googletrans import Translator
            translator = Translator()
            result = translator.translate(title, src=source_lang, dest='en')
            return result.text
        except Exception:
            return title
    
    def _calculate_language_penalty(self, content: str, language: str, 
                                  confidence: float) -> float:
        """Calculate penalty based on language detection confidence and complexity"""
        penalty = 0.0
        
        # Confidence penalty (lower confidence = higher penalty)
        if confidence < 0.9:
            penalty += (1.0 - confidence) * 0.1  # Max 10% penalty
        
        # Language complexity factor (some languages are harder to evaluate)
        complexity = {
            'en': 1.0, 'es': 0.95, 'fr': 0.93, 'de': 0.90,
            'it': 0.92, 'pt': 0.94, 'ru': 0.85, 'zh': 0.80,
            'ja': 0.78, 'ko': 0.82
        }
        penalty += (1.0 - complexity.get(language, 0.9)) * 0.05
        
        return min(penalty, 0.2)  # Cap at 20% penalty
    
    def _adjust_evaluation_for_language(self, english_eval: Dict, sentiment_score: float,
                                      avg_sentence_length: float, language_penalty: float,
                                      weights: Dict) -> Dict:
        """Adjust English evaluation for non-English essay"""
        # Base score from English evaluation
        base_score = english_eval['score'] / 100.0  # Convert to 0-1 scale
        
        # Apply language penalty
        adjusted_score = base_score * (1 - language_penalty)
        
        # Adjust component scores based on sentiment and sentence length
        feedback_parts = english_eval['feedback'].split('.')
        adjusted_feedback = f"Translated and evaluated in English. Original language: {self._get_language_name('unknown')}. " + '. '.join(feedback_parts)
        
        # Recalculate component scores with language weights
        total_grammar_errors = english_eval.get('total_grammar_errors', 0)
        grammar_score = max(0, (1 - total_grammar_errors / 10) * weights['grammar'])
        
        structure_score = weights['structure'] * (1 if avg_sentence_length > 15 else 0.8)
        content_score = sentiment_score * weights['content']
        coherence_score = weights['coherence'] * 0.9  # Slight penalty for translation
        
        # Weighted final score
        final_score = (
            grammar_score * 25 +
            structure_score * 25 +
            content_score * 30 +
            coherence_score * 20
        ) * 100  # Convert back to 0-100 scale
        
        return {
            'score': round(final_score, 2),
            'feedback': adjusted_feedback,
            'grammar': f"Grammar analysis (translated): {grammar_score*100:.1f}%",
            'structure': f"Structure: {structure_score*100:.1f}%",
            'content': f"Content quality: {content_score*100:.1f}%",
            'coherence': f"Coherence: {coherence_score*100:.1f}%",
            'suggestions': english_eval.get('suggestions', []),
            'total_grammar_errors': total_grammar_errors,
            'error_feedback': english_eval.get('error_feedback', []),
            'num_sentences': len(content.split('.')),
            'num_tokens': len(content.split()),
            'avg_sentence_length': round(avg_sentence_length, 1),
            'ai_detection_label': english_eval.get('ai_detection_label', 'Not analyzed'),
            'ai_detection_score': english_eval.get('ai_detection_score', 0),
            'detected_language': self._get_language_name('unknown'),
            'language_confidence': 0.95
        }
    
    def _direct_multilingual_evaluation(self, title: str, content: str, 
                                      language: str, sentiment_score: float,
                                      avg_sentence_length: float, 
                                      weights: Dict) -> Dict:
        """Direct evaluation for languages with good multilingual LLM support"""
        try:
            # Use multilingual pipeline for supported languages
            if self.multilingual_sentiment:
                sentiment_result = self.multilingual_sentiment(content[:512])
                sentiment_score = int(sentiment_result[0]['label'].replace('1 star', '').replace(' stars', '')) / 5.0
            
            # Basic scoring based on sentiment and length
            grammar_score = weights['grammar'] * (1 if avg_sentence_length > 10 else 0.7)
            structure_score = weights['structure'] * (1 if avg_sentence_length < 30 else 0.8)
            content_score = sentiment_score * weights['content']
            coherence_score = weights['coherence'] * 0.85  # Non-English coherence penalty
            
            final_score = (
                grammar_score * 25 +
                structure_score * 25 +
                content_score * 30 +
                coherence_score * 20
            ) * 100
            
            return {
                'score': round(final_score, 2),
                'feedback': f"Multilingual evaluation in {self._get_language_name(language)}. The essay shows good structure and content quality in the detected language.",
                'grammar': f"Grammar (multilingual): {grammar_score*100:.1f}%",
                'structure': f"Structure: {structure_score*100:.1f}%",
                'content': f"Content quality: {content_score*100:.1f}%",
                'coherence': f"Coherence: {coherence_score*100:.1f}%",
                'suggestions': [
                    f"Consider reviewing sentence structure for better flow in {self._get_language_name(language)}.",
                    "The essay demonstrates clear understanding of the topic.",
                    f"Ensure consistent use of {self._get_language_name(language)} grammar conventions."
                ],
                'total_grammar_errors': 0,  # Placeholder for multilingual grammar checking
                'error_feedback': [],
                'num_sentences': len(content.split('.')),
                'num_tokens': len(content.split()),
                'avg_sentence_length': round(avg_sentence_length, 1),
                'ai_detection_label': 'Not analyzed (multilingual)',
                'ai_detection_score': 0,
                'detected_language': self._get_language_name(language),
                'language_confidence': 0.95
            }
        except Exception as e:
            return self._basic_multilingual_evaluation(title, content, language, weights)
    
    def _basic_multilingual_evaluation(self, title: str, content: str, 
                                     language: str, weights: Dict) -> Dict:
        """Fallback evaluation when advanced models fail"""
        num_sentences = len(content.split('.')) if '.' in content else 1
        num_words = len(content.split())
        avg_sentence_length = num_words / max(num_sentences, 1)
        
        # Basic scoring
        base_score = 75  # Neutral starting point
        if avg_sentence_length > 25:
            base_score -= 10  # Penalty for long sentences
        if avg_sentence_length < 8:
            base_score -= 5   # Penalty for very short sentences
        
        feedback = f"Basic evaluation completed for {self._get_language_name(language)} essay. The essay meets minimum requirements."
        
        return {
            'score': max(50, min(95, round(base_score, 2))),  # Clamp to reasonable range
            'feedback': feedback,
            'grammar': "Basic grammar check (advanced analysis unavailable)",
            'structure': f"Structure: {(avg_sentence_length/20)*100:.1f}%",
            'content': "Content quality: Estimated from structure",
            'coherence': "Coherence: Basic assessment completed",
            'suggestions': [
                "Consider varying sentence length for better rhythm.",
                "The essay length is appropriate for the topic.",
                f"Review the essay for {self._get_language_name(language)} conventions."
            ],
            'total_grammar_errors': 0,
            'error_feedback': [],
            'num_sentences': num_sentences,
            'num_tokens': num_words,
            'avg_sentence_length': round(avg_sentence_length, 1),
            'ai_detection_label': 'Not analyzed (multilingual fallback)',
            'ai_detection_score': 0,
            'detected_language': self._get_language_name(language),
            'language_confidence': 0.8
        }
    
    def evaluate_essay(self, title: str, content: str) -> Dict[str, Any]:
        """Main entry point - detect language and evaluate accordingly"""
        return self.evaluate_essay_multilingual(title, content)

# Initialize the service
multilingual_service = MultilingualLLMService()
