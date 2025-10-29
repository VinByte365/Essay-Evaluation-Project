from flask_pymongo import PyMongo
import spacy

mongo = PyMongo()

nlp = None

def init_nlp():
    global nlp
    if nlp is None:
        nlp = spacy.load('en_core_web_sm')
    return nlp
