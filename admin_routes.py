from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from app import db
from models import User, History, ErrorLog
from werkzeug.security import generate_password_hash

admin = Blueprint('admin', __name__)

def is_admin(username):
    user = User.query.filter_by(username=username).first()
    return user and user.is_admin

@admin.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    current_user = get_jwt_identity()
    if not is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403

    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

@admin.route('/users', methods=['POST'])
@jwt_required()
def add_user():
    current_user = get_jwt_identity()
    if not is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403

    data = request.json
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    new_user = User(username=username, password=generate_password_hash(password), is_admin=is_admin)
    db.session.add(new_user)
    try:
        db.session.commit()
        return jsonify({"message": "User created successfully"}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@admin.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    current_user = get_jwt_identity()
    if not is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    try:
        db.session.commit()
        return jsonify({"message": "User deleted successfully"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@admin.route('/logs', methods=['GET'])
@jwt_required()
def get_logs():
    current_user = get_jwt_identity()
    if not is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403

    logs = ErrorLog.query.order_by(ErrorLog.created_at.desc()).limit(100).all()
    return jsonify([log.to_dict() for log in logs]), 200

@admin.route('/transcriptions', methods=['GET'])
@jwt_required()
def get_all_transcriptions():
    current_user = get_jwt_identity()
    if not is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403

    transcriptions = History.query.order_by(History.created_at.desc()).limit(100).all()
    return jsonify([transcription.to_dict() for transcription in transcriptions]), 200

@admin.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    current_user = get_jwt_identity()
    if not is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403

    total_users = User.query.count()
    total_transcriptions = History.query.count()
    total_errors = ErrorLog.query.count()

    return jsonify({
        "total_users": total_users,
        "total_transcriptions": total_transcriptions,
        "total_errors": total_errors
    }), 200