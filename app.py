from flask import Flask, request, jsonify, send_file
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
# from docx import Document
import os
from datetime import datetime
from admin_routes import admin
from drive_utils import download_from_drive  # Import the new function
from models import User, History
from dotenv import load_dotenv
from database import db
load_dotenv()  # Add this near the top of your app.py

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')  # Change this in production!
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # Configuration for file uploads

jwt = JWTManager(app)
db.init_app(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register the admin blueprint
app.register_blueprint(admin, url_prefix='/admin')

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token, is_admin=user.is_admin), 200
    return jsonify({"msg": "Bad username or password"}), 401

@app.route('/process', methods=['POST'])
@jwt_required()
def process_audio():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    audio_data = None
    if 'file' in request.files:
        audio_file = request.files['file']
        audio_data = audio_file.read()
    elif 'drive_link' in request.form:
        drive_link = request.form['drive_link']
        audio_data = download_from_drive(drive_link)
    
    if not audio_data:
        return jsonify({"error": "No audio data provided"}), 400

    try:
        # Call ASR AI API
        transcription = call_asr_api(audio_data)

        # Generate Word document
        doc_path = generate_word_document(transcription)

        # Store document locally
        local_path = store_locally(doc_path)

        # Save to history
        history = History(user_id=user.id, document_path=local_path)
        db.session.add(history)
        db.session.commit()

        return jsonify({"message": "Processing complete", "document_url": f"/download/{os.path.basename(local_path)}"}), 200
    except Exception as e:
        error_message = str(e)
        history = History(user_id=user.id, status='error', error_message=error_message)
        db.session.add(history)
        db.session.commit()
        return jsonify({"error": error_message}), 500

@app.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    user_history = History.query.filter_by(user_id=user.id).all()
    return jsonify([{
        "id": h.id,
        "created_at": h.created_at,
        "document_path": f"/download/{os.path.basename(h.document_path)}",
        "status": h.status,
        "error_message": h.error_message
    } for h in user_history]), 200

@app.route('/download/<filename>', methods=['GET'])
@jwt_required()
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

@app.route('/admin/users', methods=['POST'])
@jwt_required()
def add_user():
    current_user = User.query.filter_by(username=get_jwt_identity()).first()
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    username = request.json.get('username')
    password = request.json.get('password')
    is_admin = request.json.get('is_admin', False)

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    new_user = User(username=username, password=generate_password_hash(password), is_admin=is_admin)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201

@app.route('/admin/logs', methods=['GET'])
@jwt_required()
def get_logs():
    current_user = User.query.filter_by(username=get_jwt_identity()).first()
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    logs = History.query.filter_by(status='error').all()
    return jsonify([{
        "id": log.id,
        "user_id": log.user_id,
        "created_at": log.created_at,
        "error_message": log.error_message
    } for log in logs]), 200

def call_asr_api(audio_data):
    # Implement ASR API call here
    print("call_asr_api")
    return "call_asr_api"

def generate_word_document(transcription):
    print("generate_word_document")
    # doc = Document()
    # doc.add_heading('Sermon Transcription', 0)
    # doc.add_paragraph(transcription)
    # file_path = f"/tmp/{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
    # doc.save(file_path)
    # return file_path

def store_locally(file_path):
    file_name = os.path.basename(file_path)
    destination = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
    os.rename(file_path, destination)
    return destination

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)