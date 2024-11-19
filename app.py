import traceback
from flask import Flask, request, jsonify, send_file
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import os
from admin_routes import admin
from drive_utils import download_from_drive  # Import the new function
from models import User, Transcription, ErrorLog  # Change this import
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
    file_path = None
    drive_url = None

    if 'file' in request.files:
        audio_file = request.files['file']
        audio_data = audio_file.read()
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_file.filename)
        with open(file_path, 'wb') as f:
            f.write(audio_data)
    elif 'drive_link' in request.form:
        drive_url = request.form['drive_link']
        audio_data = download_from_drive(drive_url)

    if not audio_data:
        return jsonify({"error": "No audio data provided"}), 400

    try:
        # Create transcription record
        transcription = Transcription(
            user_id=user.id,
            audio_file_path=file_path,
            google_drive_url=drive_url,
            status='processing'
        )
        db.session.add(transcription)
        db.session.commit()

        # Generate documents
        txt_path = call_asr_api(audio_data)
        md_path = generate_md_document(txt_path)
        word_path = generate_word_document(md_path)

        # Update transcription record
        transcription.word_document_path = word_path
        transcription.txt_document_path = txt_path
        transcription.md_document_path = md_path
        transcription.status = 'completed'
        db.session.commit()

        return jsonify({
            "message": "Processing complete",
            "document_urls": {
                "txt": f"/download/{os.path.basename(txt_path)}",
                "md": f"/download/{os.path.basename(md_path)}",
                "word": f"/download/{os.path.basename(word_path)}",
            }
        }), 200

    except Exception as e:
        # Log error
        error_log = ErrorLog(
            user_id=user.id,
            transcription_id=transcription.id,
            error_message=str(e),
            stack_trace=traceback.format_exc()
        )
        transcription.status = 'error'
        db.session.add(error_log)
        db.session.commit()
        return jsonify({"error": str(e)}), 500

@app.route('/transcription', methods=['GET'])
@jwt_required()
def get_transcription():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    transcriptions = Transcription.query.filter_by(user_id=user.id).all()
    return jsonify([{
        "id": t.id,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
        "status": t.status,
        "documents": {
            "txt": f"/download/{os.path.basename(t.txt_document_path)}" if t.txt_document_path else None,
            "md": f"/download/{os.path.basename(t.md_document_path)}" if t.md_document_path else None,
            "word": f"/download/{os.path.basename(t.word_document_path)}" if t.word_document_path else None,
        }
    } for t in transcriptions]), 200

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

    logs = ErrorLog.query.filter_by(status='error').all()
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
    # Implement WORD document generation logic here
    # Return the path to the generated WORD document

def generate_txt_document(transcription):
    print("generate_txt_document")
    # Implement TXT document generation logic here
    # Return the path to the generated TXT document

def generate_md_document(transcription):
    print("generate_md_document")
    # Implement MD document generation logic here
    # Return the path to the generated MD document

def store_locally(file_path):
    file_name = os.path.basename(file_path)
    destination = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
    os.rename(file_path, destination)
    return destination

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)