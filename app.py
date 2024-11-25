from pathlib import Path
import traceback
from flask import Flask, request, jsonify, send_file
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import os
from admin_routes import admin
from models import User, Transcription, ErrorLog  # Change this import
from dotenv import load_dotenv
from database import db
from transcription_api import TranscriptionService
from time import time
import gdown  # Add this import
load_dotenv()  # Add this near the top of your app.py

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')  # Change this in production!
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['AUDIO_FOLDER'] = 'audio'  # Configuration for file uploads
app.config['TXT_FOLDER'] = 'txt'
app.config['MD_FOLDER'] = 'md'
app.config['WORD_FOLDER'] = 'word'

jwt = JWTManager(app)
db.init_app(app)

# Ensure all folders exists
os.makedirs(app.config['AUDIO_FOLDER'], exist_ok=True)
os.makedirs(app.config['TXT_FOLDER'], exist_ok=True)
os.makedirs(app.config['MD_FOLDER'], exist_ok=True)
os.makedirs(app.config['WORD_FOLDER'], exist_ok=True)

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
    file_path = None
    drive_url = None

    if 'file' in request.files:
        audio_file = request.files['file']
        audio_data = audio_file.read()
        file_path = os.path.join(app.config['AUDIO_FOLDER'], audio_file.filename)
        with open(file_path, 'wb') as f:
            f.write(audio_data)
    elif 'drive_link' in request.form:
        drive_url = request.form['drive_link']
        folder_path = os.path.join(app.config['AUDIO_FOLDER'], "")
        try:
            file_path = gdown.download(drive_url, folder_path, fuzzy=True)
            if file_path is None:
                raise Exception("Download failed. Please check if the Google Drive link is valid and publicly accessible.")
        except Exception as e:
            return jsonify({"error": f"Invalid Google Drive URL. Please make sure the link is correct and the file is publicly accessible. ({e})"}), 400
        # file_path = drive_url
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "No audio data provided or download failed"}), 400

    try:
        # Create transcription record
        transcription = Transcription(
            user_id=user.id,
            audio_file_path=file_path,
            google_drive_url=drive_url,
            status='transcribing'
        )
        db.session.add(transcription)
        db.session.commit()

        # First step: Transcribe only
        txt_path = transcribe_audio(file_path)
        transcription.txt_document_path = txt_path

        transcription.status = 'proofreading'
        db.session.commit()
        # Second step: Proofread and generate other formats
        md_path = proofread_text(txt_path)
        transcription.md_document_path = md_path

        transcription.status = 'converting'
        db.session.commit()
        word_path = convert_md_to_word(md_path)
        transcription.word_document_path = word_path

        # Final update to transcription record
        transcription.status = 'completed'
        db.session.commit()

        return jsonify({
            "message": "Processing complete",
        }), 200

    except Exception as e:
        print(f"An error occurred: {e}")
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

@app.route('/transcriptions', methods=['GET'])
@jwt_required()
def get_transcriptions():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    transcriptions = Transcription.query.filter_by(user_id=user.id).order_by(Transcription.created_at.desc()).all()
    return jsonify([{
        "id": t.id,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
        "status": t.status,
        "word_document_path": t.word_document_path if t.word_document_path else None
    } for t in transcriptions]), 200

@app.route('/download/word/<filename>', methods=['GET'])
@jwt_required()
def download_word_file(filename):
    return send_file(os.path.join(app.config['WORD_FOLDER'], filename), as_attachment=True)

# @app.route('/download/txt/<filename>', methods=['GET'])
# @jwt_required()
# def download_txt_file(filename):
#     return send_file(os.path.join(app.config['TXT_FOLDER'], filename), as_attachment=True)
#
# @app.route('/download/md/<filename>', methods=['GET'])
# @jwt_required()
# def download_md_file(filename):
#     return send_file(os.path.join(app.config['MD_FOLDER'], filename), as_attachment=True)
#
# @app.route('/download/audio/<filename>', methods=['GET'])
# @jwt_required()
# def download_audio_file(filename):
#     return send_file(os.path.join(app.config['AUDIO_FOLDER'], filename), as_attachment=True)

def transcribe_audio(audio_file_path):
    service = TranscriptionService()

    output_path = os.path.join(app.config['TXT_FOLDER'], f'{Path(audio_file_path).stem}.txt')
    # Transcribe only
    success, txt_path, error = service.transcribe(audio_file_path, output_path)
    if not success:
        raise Exception(f"Transcription failed: {error}")
    
    return txt_path

def proofread_text(txt_path):
    service = TranscriptionService()

    output_path = os.path.join(app.config['MD_FOLDER'], f'{Path(txt_path).stem}.md')
    # Proofread the transcribed text
    success, md_path, error = service.proofread(txt_path, output_path)
    if not success:
        raise Exception(f"Proofreading failed: {error}")
    
    return md_path

def convert_md_to_word(md_path):
    service = TranscriptionService()
    
    output_file = os.path.join(app.config['WORD_FOLDER'], f'{Path(md_path).stem}.docx')
    reference_doc = 'reference_pandoc.docx'
    success, docx_path, error = service.convert_to_docx(md_path, output_file, reference_doc)
    if not success:
        raise Exception(f"DOCX conversion failed: {error}")
    
    return docx_path

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)