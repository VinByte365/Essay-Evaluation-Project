from flask import Flask, send_from_directory
from flask_cors import CORS, cross_origin
from flask_mail import Mail  # ✅ Import Mail
import os
from .config import Config
from .extensions import mongo, init_nlp

# ✅ Initialize Mail object
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB
    
    # ✅ Mailtrap Email Configuration
    app.config['MAIL_SERVER'] = 'sandbox.smtp.mailtrap.io'  # Mailtrap SMTP server
    app.config['MAIL_PORT'] = 2525  # Mailtrap port
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'your-mailtrap-username')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your-mailtrap-password')
    app.config['MAIL_DEFAULT_SENDER'] = 'noreply@soessay.com'
    
    mongo.init_app(app)
    mail.init_app(app)  # ✅ Initialize mail
    
    # CORS configuration
    app.config['CORS_HEADERS'] = 'Content-Type'
    
    CORS(app, 
         resources={r"/*": {"origins": "*"}},
         supports_credentials=False,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
         expose_headers=['Content-Type', 'Authorization'])
    
    print("🔧 CORS configured: ALL methods enabled for ALL origins")
    print("📧 Mailtrap email configured")  # ✅ Add confirmation

    # Configure upload folder
    UPLOAD_FOLDER = 'uploads/avatars'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Add route to serve uploaded avatar files
    @app.route('/uploads/avatars/<filename>')
    def uploaded_file(filename):
        """Serve uploaded avatar files"""
        upload_path = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'])
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
    
    from app.routes.notifications import notifications_bp
    app.register_blueprint(notifications_bp, url_prefix='/api')

    return app
