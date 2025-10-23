from flask_pymongo import PyMongo
import spacy
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

mongo = PyMongo()

detector_pipe = None

def init_detector():
    global detector_pipe
    if detector_pipe is None:
        model_name = 'roberta-base-openai-detector'
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        detector_pipe = pipeline('text-classification', model=model, tokenizer=tokenizer)
    return detector_pipe

nlp = None

def init_nlp():
    global nlp
    if nlp is None:
        nlp = spacy.load('en_core_web_sm')
    return nlp
