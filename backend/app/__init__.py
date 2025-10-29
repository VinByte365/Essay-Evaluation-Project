from flask import Flask, send_from_directory
from flask_cors import CORS
import os
from .config import Config
from .extensions import mongo, init_nlp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB
 
    mongo.init_app(app)
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        },
        r"/uploads/*": {  # Add CORS for uploads
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    })

    # Configure upload folder
    UPLOAD_FOLDER = 'uploads/avatars'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Add route to serve uploaded avatar files
    @app.route('/uploads/avatars/<filename>')
    def uploaded_file(filename):
        """Serve uploaded avatar files"""
        upload_path = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'])
        print(f"🔍 Serving file: {filename}")
        print(f"📂 From directory: {upload_path}")
        print(f"📂 Full path: {os.path.join(upload_path, filename)}")
        print(f"📂 File exists: {os.path.exists(os.path.join(upload_path, filename))}")
        return send_from_directory(upload_path, filename)

    with app.app_context():
        init_nlp()

    from .routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.routes.posts import posts_bp
    app.register_blueprint(posts_bp, url_prefix='/api')

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from app.routes.friends import friends_bp
    app.register_blueprint(friends_bp, url_prefix='/api')

    from app.routes.search import search_bp
    app.register_blueprint(search_bp, url_prefix='/api')
    
    return app
