import datetime
import logging
from pathlib import Path
import sys
import traceback
from flask import Flask, request, jsonify, send_file
from flask_executor import Executor
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import check_password_hash
import os
from admin_routes import admin
from models import User, Transcription, ErrorLog
from dotenv import load_dotenv
from database import db
from TranscriptionService import TranscriptionService
import gdown
load_dotenv()

logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(message)s"
    )
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')  # Change this in production!
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['AUDIO_FOLDER'] = 'audio'
app.config['TXT_FOLDER'] = 'txt'
app.config['MD_FOLDER'] = 'md'
app.config['WORD_FOLDER'] = 'word'

jwt = JWTManager(app)
db.init_app(app)

# Register the admin blueprint
app.register_blueprint(admin, url_prefix='/admin')

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        access_token = create_access_token(identity=username, expires_delta=datetime.timedelta(days=1))
        return jsonify(access_token=access_token, is_admin=user.is_admin), 200
    return jsonify({"msg": "Bad username or password"}), 401

executor = Executor(app)

@app.route('/process', methods=['POST'])
@jwt_required()
def process_audio():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    file_path = None
    drive_url = None
    os.makedirs(os.path.join(app.config['AUDIO_FOLDER'], user.username), exist_ok=True)

    if 'file' in request.files:
        audio_file = request.files['file']
        audio_data = audio_file.read()
        file_path = os.path.join(app.config['AUDIO_FOLDER'], user.username, audio_file.filename)
        with open(file_path, 'wb') as f:
            f.write(audio_data)
    elif 'drive_link' in request.form:
        drive_url = request.form['drive_link']
        folder_path = os.path.join(app.config['AUDIO_FOLDER'], user.username, "")
        try:
            file_path = gdown.download(drive_url, folder_path, fuzzy=True)
            if file_path is None:
                raise Exception("Download failed. Please check if the Google Drive link is valid and publicly accessible.")
        except Exception as e:
            return jsonify({"error": f"Invalid Google Drive URL. Please make sure the link is correct and the file is publicly accessible. ({e})"}), 400
        # file_path = drive_url
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "No audio data provided or download failed"}), 400

    executor.submit(process_transcription, user, file_path, drive_url)
    return jsonify({
        "message": "Transcription request is submitted",
    }), 200


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
        "word_document_path": t.word_document_path if t.word_document_path else None,
        "audio_file_name": f'{Path(t.audio_file_path).stem}'
    } for t in transcriptions]), 200

@app.route('/download/word/<username>/<filename>', methods=['GET'])
@jwt_required()
def download_word_file(username, filename):
    user = User.query.filter_by(username=get_jwt_identity()).first()
    if (username != user.username):
        return jsonify({"error": "Unauthorized access"}), 403

    return send_file(os.path.join(app.config['WORD_FOLDER'], user.username, filename), as_attachment=True)

# @app.route('/download/txt/<username>/<filename>', methods=['GET'])
# @jwt_required()
# def download_txt_file(username, filename):
#     user = User.query.filter_by(username=get_jwt_identity()).first()
#     if (username != user.username):
#         return jsonify({"error": "Unauthorized access"}), 403

#     return send_file(os.path.join(app.config['TXT_FOLDER'], user.username, filename), as_attachment=True)

# @app.route('/download/md/<username>/<filename>', methods=['GET'])
# @jwt_required()
# def download_md_file(username, filename):
#     user = User.query.filter_by(username=get_jwt_identity()).first()
#     if (username != user.username):
#         return jsonify({"error": "Unauthorized access"}), 403

#     return send_file(os.path.join(app.config['MD_FOLDER'], user.username, filename), as_attachment=True)

# @app.route('/download/audio/<username>/<filename>', methods=['GET'])
# @jwt_required()
# def download_audio_file(username, filename):
#     user = User.query.filter_by(username=get_jwt_identity()).first()
#     if (username != user.username):
#         return jsonify({"error": "Unauthorized access"}), 403

#     return send_file(os.path.join(app.config['AUDIO_FOLDER'], user.username, filename), as_attachment=True)

def process_transcription(user, file_path, drive_url):
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
        txt_path = transcribe_audio(file_path, user.username)
        transcription.txt_document_path = txt_path

        transcription.status = 'proofreading'
        db.session.commit()
        # Second step: Proofread and generate other formats
        md_path = proofread_text(txt_path, user.username)
        transcription.md_document_path = md_path

        transcription.status = 'converting'
        db.session.commit()
        word_path = convert_md_to_word(md_path, user.username)
        transcription.word_document_path = word_path

        # Final update to transcription record
        transcription.status = 'completed'
        db.session.commit()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
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

def transcribe_audio(audio_file_path, username):
    service = TranscriptionService()

    os.makedirs(os.path.join(app.config['TXT_FOLDER'], username), exist_ok=True)
    output_path = os.path.join(app.config['TXT_FOLDER'], username, f'{Path(audio_file_path).stem}.txt')
    # Transcribe only
    success, txt_path, error = service.transcribe(audio_file_path, output_path)
    if not success:
        raise Exception(f"Transcription failed: {error}")
    
    return txt_path

def proofread_text(txt_path, username):
    service = TranscriptionService()

    os.makedirs(os.path.join(app.config['MD_FOLDER'], username), exist_ok=True)
    output_path = os.path.join(app.config['MD_FOLDER'], username, f'{Path(txt_path).stem}.md')
    # Proofread the transcribed text
    success, md_path, error = service.proofread(txt_path, output_path)
    if not success:
        raise Exception(f"Proofreading failed: {error}")
    
    return md_path

def convert_md_to_word(md_path, username):
    service = TranscriptionService()
    
    os.makedirs(os.path.join(app.config['WORD_FOLDER'], username), exist_ok=True)
    output_file = os.path.join(app.config['WORD_FOLDER'], username, f'{Path(md_path).stem}.docx')
    reference_doc = 'reference_pandoc.docx'
    success, docx_path, error = service.convert_to_docx(md_path, output_file, reference_doc)
    if not success:
        raise Exception(f"DOCX conversion failed: {error}")
    
    return docx_path

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)