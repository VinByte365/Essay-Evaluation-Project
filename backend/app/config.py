import os
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'devkey'
    MONGO_URI = os.environ.get('MONGO_URI')
