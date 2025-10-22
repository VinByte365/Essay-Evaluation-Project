from flask import Flask
from flask_cors import CORS
from .config import Config
from .extensions import mongo, init_nlp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB
 
    mongo.init_app(app)
    CORS(app)

    with app.app_context():
        init_nlp()

    from .routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
