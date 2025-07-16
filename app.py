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

import subprocess
from admin_routes import admin
from models import User, Transcription, ErrorLog
from dotenv import load_dotenv
from database import db
from pandoc_service import PandocService
from proofreading_service import ProofreadingService
from transcription_service import TranscriptionService
import gdown
load_dotenv()

logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(message)s"
)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.environ.get(
    'JWT_SECRET_KEY')  # Change this in production!
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ROOT_FOLDER'] = 'user-files'
app.config['AUDIO_FOLDER'] = os.path.join(app.config['ROOT_FOLDER'], 'audio')
app.config['TXT_FOLDER'] = os.path.join(app.config['ROOT_FOLDER'], 'txt')
app.config['MD_FOLDER'] = os.path.join(app.config['ROOT_FOLDER'], 'md')
app.config['WORD_FOLDER'] = os.path.join(app.config['ROOT_FOLDER'], 'word')

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
        access_token = create_access_token(
            identity=username, expires_delta=datetime.timedelta(days=365))
        return jsonify(access_token=access_token, is_admin=user.is_admin), 200
    return jsonify({"msg": "Bad username or password"}), 401


executor = Executor(app)


@app.route('/process', methods=['POST'])
@jwt_required()
def process_audio():
    user = User.query.filter_by(username=get_jwt_identity()).first()

    # Create transcription record
    transcription = Transcription(
        user_id=user.id,
        status='uploading'
    )
    db.session.add(transcription)
    db.session.commit()

    # Create user-specific directory in volume
    folder_path = os.path.join(
        app.config['AUDIO_FOLDER'], transcription.user.username, str(transcription.id), "")
    os.makedirs(folder_path, exist_ok=True)

    gdrive_or_youtube_url = request.form['drive_link']
    try:
        if 'drive.google.com' in gdrive_or_youtube_url:
            file_path = gdown.download(
                gdrive_or_youtube_url, folder_path, fuzzy=True)
        elif 'youtube.com' in gdrive_or_youtube_url or 'youtu.be' in gdrive_or_youtube_url:
            # Create cookie.txt if it doesn't exist
            cookie_path = os.path.join(app.config['ROOT_FOLDER'], 'cookie.txt')
            if not os.path.exists(cookie_path):
                with open(cookie_path, 'w', encoding='utf-8') as f:
                    f.write("""# Netscape HTTP Cookie File
# http://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.youtube.com	TRUE	/	TRUE	1748017868	GPS	1
.youtube.com	TRUE	/	TRUE	1782576107	PREF	f6=40000000&tz=Asia.Bangkok
.youtube.com	TRUE	/	TRUE	1779552105	__Secure-1PSIDTS	sidts-CjIBjplskLpWZbVTb2AwbA3PKv9068JsrIKIQITu-a-GLb8mlE66AzcTGrO3wsfhW7xJqRAA
.youtube.com	TRUE	/	TRUE	1779552105	__Secure-3PSIDTS	sidts-CjIBjplskLpWZbVTb2AwbA3PKv9068JsrIKIQITu-a-GLb8mlE66AzcTGrO3wsfhW7xJqRAA
.youtube.com	TRUE	/	FALSE	1782576105	HSID	AWe4V53nudcq29S4H
.youtube.com	TRUE	/	TRUE	1782576105	SSID	AA2-ZQBDGCw8Pi8Hh
.youtube.com	TRUE	/	FALSE	1782576105	APISID	IcR07fZgTNiKOmM8/AoDVFZehUNIyVaPvb
.youtube.com	TRUE	/	TRUE	1782576105	SAPISID	Kuk8NC7snSSbd_Ir/ALoQbRMdRO7zPU0PN
.youtube.com	TRUE	/	TRUE	1782576105	__Secure-1PAPISID	Kuk8NC7snSSbd_Ir/ALoQbRMdRO7zPU0PN
.youtube.com	TRUE	/	TRUE	1782576105	__Secure-3PAPISID	Kuk8NC7snSSbd_Ir/ALoQbRMdRO7zPU0PN
.youtube.com	TRUE	/	FALSE	1782576105	SID	g.a000xQiPZx6VsKV7bJFHiHtoSG-vpR6kpLaTSfQ2cfjOoDbjQebghoMiQ64UZc1BIo_J5W4yuwACgYKAfYSARESFQHGX2MiOFi6gQeymGWq5Q0MDXT8ZxoVAUF8yKrE9dAMX4tiD_McqkxIuBE_0076
.youtube.com	TRUE	/	TRUE	1782576105	__Secure-1PSID	g.a000xQiPZx6VsKV7bJFHiHtoSG-vpR6kpLaTSfQ2cfjOoDbjQebgJgBtTvZcK6zhr55rA-x5GwACgYKAX8SARESFQHGX2MiSZQEc1jMSh8p8bPCx2KieBoVAUF8yKpL-G5-rQXRqTzlLpPqLqeN0076
.youtube.com	TRUE	/	TRUE	1782576105	__Secure-3PSID	g.a000xQiPZx6VsKV7bJFHiHtoSG-vpR6kpLaTSfQ2cfjOoDbjQebg87VEgoR0gPNvbpLyO8mikgACgYKAV8SARESFQHGX2MiWKdMabKDggbL5VMO3fFwjxoVAUF8yKq6CRorOoIwhICIybAVLNLp0076
.youtube.com	TRUE	/	TRUE	1782576105	LOGIN_INFO	AFmmF2swRAIgSUh4HA1nXpx1XmLwznZWh6-ef8ZMmNn0yxsad0tJC9wCIDILWmnkJPGbZ91OBXz3WpDN5r0mr2ODttsBjypLM6jV:QUQ3MjNmd1g1eHVibGpVNFdFSHF3bm1BdE9PQ0RUQWxGd2JlOS00R1REZFh3MHVJR1Z6WERWMlFLSmJnRHF3NEVQWUwwNWdEVUd1THB0NGpWN1RPcjVhZFAzTzdHMEZiTHRjOHFGQ3ZhSDR6TG9ETlA3cjlPVUI0ZnJNeXIxdUZRdGZCUUpEZFV0c3otNEFpbHpEMXgtMUtPX1pXZ3Q3UmRR
.youtube.com	TRUE	/	FALSE	1779552180	SIDCC	AKEyXzWYiWyz903ojmyKvlVtYa3YriM0eSaCBEpHNFioxQ3g0xXgjTPBvDI_Ezdgh0RB0ZJ9
.youtube.com	TRUE	/	TRUE	1779552180	__Secure-1PSIDCC	AKEyXzXmS3fSeTKhO3h9fno59AeUPbYQ8fmaPZkPf0FsNqbN4sausEQoW3RFVtwJdo8DapTxKQ
.youtube.com	TRUE	/	TRUE	1779552180	__Secure-3PSIDCC	AKEyXzX2WzVuSZtcFnqoZHT2qdrXTlOtW_lygpLvi59AexnsxL0CUee2CY2bmvS2dy6QOZa5Ng
.youtube.com	TRUE	/	TRUE	0	YSC	Y8XiqMqbGiY
.youtube.com	TRUE	/	TRUE	1763568110	VISITOR_INFO1_LIVE	zTNhRm4ZWK8
.youtube.com	TRUE	/	TRUE	1763568110	VISITOR_PRIVACY_METADATA	CgJJRBIEGgAgJg%3D%3D
.youtube.com	TRUE	/	TRUE	1763568070	__Secure-ROLLOUT_TOKEN	CNXy_9L766DYARDH5P2m-7mNAxjwvaSo-7mNAw%3D%3D
""")
            # Update yt-dlp to latest version
            try:
                subprocess.run(['yt-dlp', '--update'], capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError:
                # If update fails, continue anyway as yt-dlp might still work
                pass
            
            # Use yt-dlp executable
            cmd = [
                'yt-dlp',
                '--format', 'bestaudio/best',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '192K',
                '--output', folder_path + '%(title)s.%(ext)s',
                '--cookies', cookie_path,
                # '--ffmpeg-location', '/usr/bin/ffmpeg',
                gdrive_or_youtube_url
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                # Get the filename from the output
                output_lines = result.stdout.strip().split('\n')
                file_path = None
                for line in output_lines:
                    if line.strip() and os.path.exists(line.strip()):
                        file_path = line.strip()
                        break
                
                if not file_path:
                    # If we can't find the exact file, look for any mp3 file in the folder
                    for file in os.listdir(folder_path):
                        if file.endswith('.mp3'):
                            file_path = os.path.join(folder_path, file)
                            break
            except subprocess.CalledProcessError as e:
                raise Exception(f"yt-dlp command failed: {e.stderr}")
        if file_path is None:
            raise Exception(
                "Download failed. Please check if the Google Drive link or YouTube URL is valid and publicly accessible.")
    except Exception as e:
        transcription.status = 'error'
        db.session.commit()
        return {"error": f"""Invalid Google Drive URL or YouTube URL. Please make sure the link is correct and the file is publicly accessible. ({e})"""}, 400

    if not file_path or not os.path.exists(file_path):
        transcription.status = 'error'
        db.session.commit()
        return {"error": "No audio data provided or download failed"}, 400

    transcription.audio_file_path = file_path
    db.session.commit()

    # file_path = None
    # drive_url = None
    # os.makedirs(os.path.join(
    #     app.config['AUDIO_FOLDER'], user.username, str(transcription.id)), exist_ok=True)

    # if 'file' in request.files:
    #     audio_file = request.files['file']
    #     audio_data = audio_file.read()
    #     file_path = os.path.join(
    #         app.config['AUDIO_FOLDER'], user.username, str(transcription.id), audio_file.filename)
    #     with open(file_path, 'wb') as f:
    #         f.write(audio_data)
    # elif 'drive_link' in request.form:
    #     drive_url = request.form['drive_link']
    #     folder_path = os.path.join(
    #         app.config['AUDIO_FOLDER'], user.username, str(transcription.id), "")
    #     try:
    #         file_path = gdown.download(drive_url, folder_path, fuzzy=True)
    #         if file_path is None:
    #             raise Exception(
    #                 "Download failed. Please check if the Google Drive link is valid and publicly accessible.")
    #     except Exception as e:
    #         transcription.status = 'error'
    #         db.session.commit()
    #         return jsonify({"error": f"""Invalid Google Drive URL. Please make sure the link is correct and the file is publicly accessible. ({e})"""}), 400
    #     # file_path = drive_url

    # if not file_path or not os.path.exists(file_path):
    #     transcription.status = 'error'
    #     db.session.commit()
    #     return jsonify({"error": "No audio data provided or download failed"}), 400

    # transcription.audio_file_path = file_path
    transcription.google_drive_url = gdrive_or_youtube_url
    db.session.commit()

    executor.submit(process_transcription, transcription.id)
    return jsonify({
        "message": "Transcription request is submitted",
    }), 200


@app.route('/transcriptions', methods=['GET'])
@jwt_required()
def get_transcriptions():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    transcriptions = Transcription.query.filter_by(
        user_id=user.id).order_by(Transcription.created_at.desc()).all()
    return jsonify([{
        "id": t.id,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
        "status": t.status,
        "word_document_path": t.word_document_path if t.word_document_path else None,
        "txt_document_path": t.txt_document_path if t.txt_document_path else None,
        "audio_file_name": f"""{Path(t.audio_file_path).stem}""" if t.audio_file_path else t.google_drive_url,
    } for t in transcriptions]), 200


@app.route('/download/word/<username>/<transcription_id>/<filename>', methods=['GET'])
@jwt_required()
def download_word_file(username, transcription_id, filename):
    user = User.query.filter_by(username=get_jwt_identity()).first()
    if (username != user.username):
        return jsonify({"error": "Unauthorized access"}), 403

    return send_file(os.path.join(app.config['WORD_FOLDER'], user.username, transcription_id, filename), as_attachment=True)

# @app.route('/download/audio/<username>/<transcription_id>/<filename>', methods=['GET'])
# @jwt_required()
# def download_audio_file(username, transcription_id, filename):
#     user = User.query.filter_by(username=get_jwt_identity()).first()
#     if (username != user.username):
#         return jsonify({"error": "Unauthorized access"}), 403

#     return send_file(os.path.join(app.config['AUDIO_FOLDER'], user.username, transcription_id, filename), as_attachment=True)


@app.route('/download/txt/<username>/<transcription_id>/<filename>', methods=['GET'])
@jwt_required()
def download_txt_file(username, transcription_id, filename):
    user = User.query.filter_by(username=get_jwt_identity()).first()
    if (username != user.username):
        return jsonify({"error": "Unauthorized access"}), 403

    return send_file(os.path.join(app.config['TXT_FOLDER'], user.username, transcription_id, filename), as_attachment=True)

# @app.route('/download/md/<username>/<transcription_id>/<filename>', methods=['GET'])
# @jwt_required()
# def download_md_file(username, transcription_id, filename):
#     user = User.query.filter_by(username=get_jwt_identity()).first()
#     if (username != user.username):
#         return jsonify({"error": "Unauthorized access"}), 403

#     return send_file(os.path.join(app.config['MD_FOLDER'], user.username, transcription_id, filename), as_attachment=True)


def process_transcription(transcription_id: str):
    try:
        transcription: Transcription = Transcription.query.get(
            transcription_id)

        def transcribe_audio(transcription: Transcription):
            os.makedirs(os.path.join(
                app.config['TXT_FOLDER'], transcription.user.username, str(transcription.id)), exist_ok=True)
            output_path = os.path.join(app.config['TXT_FOLDER'], transcription.user.username, str(transcription.id))

            # Transcribe only
            success, txt_path, error = TranscriptionService(
            ).transcribe(output_path, transcription)

            if not success:
                transcription.status = 'error'
                db.session.commit()
                raise Exception(f"""Transcription failed: {error}""")
            return txt_path

        def proofread_text(transcription: Transcription):
            os.makedirs(os.path.join(
                app.config['MD_FOLDER'], transcription.user.username, str(transcription.id)), exist_ok=True)
            output_path = os.path.join(app.config['MD_FOLDER'], transcription.user.username, str(transcription.id), f"""{
                                       Path(transcription.txt_document_path).stem}.md""")
            # Proofread the transcribed text
            success, md_path, error = ProofreadingService().proofread(transcription, output_path)
            if not success:
                raise Exception(f"""Proofreading failed: {error}""")

            return md_path

        def convert_md_to_word(transcription: Transcription):
            os.makedirs(os.path.join(
                app.config['WORD_FOLDER'], transcription.user.username, str(transcription.id)), exist_ok=True)
            output_file = os.path.join(app.config['WORD_FOLDER'], transcription.user.username, str(transcription.id), f"""{
                                       Path(transcription.md_document_path).stem}.docx""")
            reference_doc = 'reference_pandoc.docx'
            success, docx_path, error = PandocService().convert_to_docx(
                transcription.md_document_path, output_file, reference_doc)
            if not success:
                raise Exception(f"""DOCX conversion failed: {error}""")

            return docx_path

        transcription.status = 'waiting'
        db.session.commit()
        # First step: Transcribe only
        txt_path = transcribe_audio(transcription)
        transcription.txt_document_path = txt_path

        transcription.status = 'proofreading'
        db.session.commit()
        # Second step: Proofread and generate other formats
        md_path = proofread_text(transcription)
        transcription.md_document_path = md_path

        transcription.status = 'converting'
        db.session.commit()
        word_path = convert_md_to_word(transcription)
        transcription.word_document_path = word_path

        # Final update to transcription record
        transcription.status = 'completed'
        db.session.commit()
        logging.info(f"""Transcription {f"""{Path(transcription.audio_file_path).stem}""" if transcription.audio_file_path else transcription.google_drive_url} completed successfully""")

    except Exception as e:
        logging.error(f"""An error occurred: {e}""")
        # Log error
        error_log = ErrorLog(
            user_id=transcription.user.id,
            transcription_id=transcription.id,
            error_message=str(e),
            stack_trace=traceback.format_exc()
        )
        transcription.status = 'error'
        db.session.add(error_log)
        db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
