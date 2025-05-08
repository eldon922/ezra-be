from functools import wraps
import os
import shutil
from flask import Blueprint, current_app, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from database import db
from models import ProofreadPrompt, SystemSetting, TranscribePrompt, User, Transcription, ErrorLog
from werkzeug.security import generate_password_hash

admin = Blueprint('admin', __name__)


def is_admin(username):
    user = User.query.filter_by(username=username).first()
    if user:
        return user.is_admin
    return False


def require_admin(func):
    @wraps(func)  # Keeps the original function metadata
    def wrapper(*args, **kwargs):
        current_user = get_jwt_identity()
        if not is_admin(current_user):
            return jsonify({"error": "Admin access required"}), 403
        # Call the actual function only if authorized
        return func(*args, **kwargs)
    return wrapper


@admin.route('/users', methods=['GET'])
@jwt_required()
@require_admin
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200


@admin.route('/users', methods=['POST'])
@jwt_required()
@require_admin
def add_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    is_new_user_admin = data.get('isAdmin', False)

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    new_user = User(username=username, password=generate_password_hash(
        password), is_admin=is_new_user_admin)
    db.session.add(new_user)
    try:
        db.session.commit()
        return jsonify({"message": "User created successfully"}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@require_admin
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.is_admin:
        return jsonify({"error": "User is admin"}), 404

    try:
        # Delete associated records from related tables
        ErrorLog.query.filter_by(user_id=user_id).delete()
        Transcription.query.filter_by(user_id=user_id).delete()

        # Delete the user
        db.session.delete(user)

        # Delete associated files
        user_folders = [
            # os.path.join(current_app.config['AUDIO_FOLDER'], user.username),
            os.path.join(current_app.config['TXT_FOLDER'], user.username),
            os.path.join(current_app.config['MD_FOLDER'], user.username),
            os.path.join(current_app.config['WORD_FOLDER'], user.username)
        ]

        # Commit database changes first
        db.session.commit()

        # Then handle file system operations
        for folder in user_folders:
            if os.path.exists(folder):
                shutil.rmtree(folder)
        return jsonify({"message": "User and all associated data deleted successfully"}), 200

    except OSError as e:
        db.session.rollback()
        return jsonify({"error": f"""Error deleting user files: {str(e)}"""}), 500
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"""Database error: {str(e)}"""}), 500


@admin.route('/transcriptions/<string:transcription_id>', methods=['DELETE'])
@jwt_required()
@require_admin
def delete_transcription(transcription_id):
    transcription: Transcription = Transcription.query.get(transcription_id)
    if not transcription:
        return jsonify({"error": "Transcription not found"}), 404

    try:
        # Delete associated records from related tables
        ErrorLog.query.filter_by(transcription_id=transcription_id).delete()

        # Delete the user
        db.session.delete(transcription)

        # Delete associated files
        transcription_folders = [
            # os.path.join(current_app.config['AUDIO_FOLDER'], transcription.user.username, transcription_id),
            os.path.join(current_app.config['TXT_FOLDER'], transcription.user.username, transcription_id),
            os.path.join(current_app.config['MD_FOLDER'], transcription.user.username, transcription_id),
            os.path.join(current_app.config['WORD_FOLDER'], transcription.user.username, transcription_id)
        ]

        # Commit database changes first
        db.session.commit()

        # Then handle file system operations
        for folder in transcription_folders:
            if os.path.exists(folder):
                for file in os.listdir(folder):
                    os.remove(os.path.join(folder, file))
                os.rmdir(folder)
        return jsonify({"message": "Transcription and all associated data deleted successfully"}), 200

    except OSError as e:
        db.session.rollback()
        return jsonify({"error": f"""Error deleting transcription files: {str(e)}"""}), 500
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"""Database error: {str(e)}"""}), 500


@admin.route('/logs', methods=['GET'])
@jwt_required()
@require_admin
def get_logs():
    logs = ErrorLog.query.order_by(ErrorLog.created_at.desc()).limit(100).all()
    return jsonify([log.to_dict() for log in logs]), 200


@admin.route('/transcriptions', methods=['GET'])
@jwt_required()
@require_admin
def get_all_transcriptions():
    transcriptions = Transcription.query.order_by(
        Transcription.created_at.desc()).limit(100).all()
    return jsonify([transcription.to_dict() for transcription in transcriptions]), 200


@admin.route('/transcribe-prompts', methods=['GET'])
@jwt_required()
@require_admin
def get_all_transcribe_prompts():
    transcribe_prompts = TranscribePrompt.query.order_by(
        TranscribePrompt.created_at.desc()).limit(100).all()
    return jsonify([transcribe_prompt.to_dict() for transcribe_prompt in transcribe_prompts]), 200


@admin.route('/transcribe-prompts', methods=['POST'])
@jwt_required()
@require_admin
def add_transcribe_prompt():
    data = request.json
    version = data.get('version')
    prompt = data.get('prompt')

    if not version or not prompt:
        return jsonify({"error": "Version and prompt are required"}), 400

    new_prompt = TranscribePrompt(version=version, prompt=prompt)
    db.session.add(new_prompt)
    try:
        db.session.commit()
        return jsonify({"message": "Transcribe prompt created successfully"}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin.route('/settings/active-transcribe-prompt', methods=['GET'])
@jwt_required()
@require_admin
def get_active_transcribe_prompt():
    setting = SystemSetting.query.filter_by(
        setting_key='active_transcribe_prompt_id').first()
    if not setting:
        return jsonify({"error": "No active transcribe prompt set"}), 404

    prompt = TranscribePrompt.query.get(setting.setting_value)
    if not prompt:
        return jsonify({"error": "Active transcribe prompt not found"}), 404

    return jsonify(prompt.to_dict()), 200


@admin.route('/settings/active-transcribe-prompt', methods=['POST'])
@jwt_required()
@require_admin
def set_active_transcribe_prompt():
    data = request.json
    transcribe_prompt_id = data.get('transcribe_prompt_id')

    if not transcribe_prompt_id:
        return jsonify({"error": "Transcribe prompt ID is required"}), 400

    prompt = TranscribePrompt.query.get(transcribe_prompt_id)
    if not prompt:
        return jsonify({"error": "Transcribe prompt not found"}), 404

    setting = SystemSetting.query.filter_by(
        setting_key='active_transcribe_prompt_id').first()
    if setting:
        setting.setting_value = str(transcribe_prompt_id)
    else:
        setting = SystemSetting(
            setting_key='active_transcribe_prompt_id',
            setting_value=str(transcribe_prompt_id),
            description='ID of the currently active transcribe prompt'
        )
        db.session.add(setting)

    try:
        db.session.commit()
        return jsonify({"message": "Active transcribe prompt updated successfully"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin.route('/proofread-prompts', methods=['GET'])
@jwt_required()
@require_admin
def get_all_proofread_prompts():
    proofread_prompts = ProofreadPrompt.query.order_by(
        ProofreadPrompt.created_at.desc()).limit(100).all()
    return jsonify([proofread_prompt.to_dict() for proofread_prompt in proofread_prompts]), 200


@admin.route('/proofread-prompts', methods=['POST'])
@jwt_required()
@require_admin
def add_proofread_prompt():
    data = request.json
    version = data.get('version')
    prompt = data.get('prompt')

    if not version or not prompt:
        return jsonify({"error": "Version and prompt are required"}), 400

    new_prompt = ProofreadPrompt(version=version, prompt=prompt)
    db.session.add(new_prompt)
    try:
        db.session.commit()
        return jsonify({"message": "Proofread prompt created successfully"}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin.route('/settings/active-proofread-prompt', methods=['GET'])
@jwt_required()
@require_admin
def get_active_proofread_prompt():
    setting = SystemSetting.query.filter_by(
        setting_key='active_proofread_prompt_id').first()
    if not setting:
        return jsonify({"error": "No active proofread prompt set"}), 404

    prompt = ProofreadPrompt.query.get(setting.setting_value)
    if not prompt:
        return jsonify({"error": "Active proofread prompt not found"}), 404

    return jsonify(prompt.to_dict()), 200


@admin.route('/settings/active-proofread-prompt', methods=['POST'])
@jwt_required()
@require_admin
def set_active_proofread_prompt():
    data = request.json
    proofread_prompt_id = data.get('proofread_prompt_id')

    if not proofread_prompt_id:
        return jsonify({"error": "Proofread prompt ID is required"}), 400

    prompt = ProofreadPrompt.query.get(proofread_prompt_id)
    if not prompt:
        return jsonify({"error": "Proofread prompt not found"}), 404

    setting = SystemSetting.query.filter_by(
        setting_key='active_proofread_prompt_id').first()
    if setting:
        setting.setting_value = str(proofread_prompt_id)
    else:
        setting = SystemSetting(
            setting_key='active_proofread_prompt_id',
            setting_value=str(proofread_prompt_id),
            description='ID of the currently active proofread prompt'
        )
        db.session.add(setting)

    try:
        db.session.commit()
        return jsonify({"message": "Active proofread prompt updated successfully"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin.route('/settings', methods=['GET'])
@jwt_required()
@require_admin
def get_settings():
    settings = SystemSetting.query.all()
    return jsonify([setting.to_dict() for setting in settings]), 200


@admin.route('/settings', methods=['POST'])
@jwt_required()
@require_admin
def add_setting():
    data = request.json
    key = data.get('setting_key')
    value = data.get('setting_value')
    description = data.get('description')

    if not key or not value:
        return jsonify({"error": "Setting key and value are required"}), 400

    if SystemSetting.query.filter_by(setting_key=key).first():
        return jsonify({"error": "Setting key already exists"}), 400

    new_setting = SystemSetting(
        setting_key=key, setting_value=value, description=description)
    db.session.add(new_setting)
    try:
        db.session.commit()
        return jsonify({"message": "Setting created successfully"}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin.route('/settings/<int:setting_id>', methods=['PUT'])
@jwt_required()
@require_admin
def update_setting(setting_id):
    setting = SystemSetting.query.get(setting_id)
    if not setting:
        return jsonify({"error": "Setting not found"}), 404

    data = request.json
    setting.setting_value = data.get('setting_value', setting.setting_value)
    setting.description = data.get('description', setting.description)

    try:
        db.session.commit()
        return jsonify({"message": "Setting updated successfully"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin.route('/settings/<int:setting_id>', methods=['DELETE'])
@jwt_required()
@require_admin
def delete_setting(setting_id):
    setting = SystemSetting.query.get(setting_id)
    if not setting:
        return jsonify({"error": "Setting not found"}), 404

    db.session.delete(setting)
    try:
        db.session.commit()
        return jsonify({"message": "Setting deleted successfully"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin.route('/stats', methods=['GET'])
@jwt_required()
@require_admin
def get_stats():
    total_users = User.query.count()
    total_transcriptions = Transcription.query.count()
    total_errors = ErrorLog.query.count()

    return jsonify({
        "total_users": total_users,
        "total_transcriptions": total_transcriptions,
        "total_errors": total_errors
    }), 200


# @admin.route('/download/audio/<username>/<transcription_id>/<filename>', methods=['GET'])
# @jwt_required()
# @require_admin
# def download_audio_file(username, transcription_id, filename):
#     return send_file(os.path.join(current_app.config['AUDIO_FOLDER'], username, transcription_id, filename), as_attachment=True)


@admin.route('/download/txt/<username>/<transcription_id>/<filename>', methods=['GET'])
@jwt_required()
@require_admin
def download_txt_file(username, transcription_id, filename):
    return send_file(os.path.join(current_app.config['TXT_FOLDER'], username, transcription_id, filename), as_attachment=True)


@admin.route('/download/md/<username>/<transcription_id>/<filename>', methods=['GET'])
@jwt_required()
@require_admin
def download_md_file(username, transcription_id, filename):
    return send_file(os.path.join(current_app.config['MD_FOLDER'], username, transcription_id, filename), as_attachment=True)


@admin.route('/download/word/<username>/<transcription_id>/<filename>', methods=['GET'])
@jwt_required()
@require_admin
def download_word_file(username, transcription_id, filename):
    return send_file(os.path.join(current_app.config['WORD_FOLDER'], username, transcription_id, filename), as_attachment=True)
