from uuid import uuid4
from sqlalchemy import UUID
from database import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp())
    transcriptions = db.relationship('Transcription', back_populates='user')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat(),
            'transcription_count': len(self.transcriptions)
        }

class Transcription(db.Model):
    __tablename__ = 'transcriptions'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    audio_file_path = db.Column(db.Text)
    google_drive_url = db.Column(db.Text)
    txt_document_path = db.Column(db.Text)
    md_document_path = db.Column(db.Text)
    word_document_path = db.Column(db.Text)
    status = db.Column(db.Text, default='uploading')
    transcribe_prompt = db.Column(db.Text)
    proofread_prompt = db.Column(db.Text)
    inference_duration = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    user = db.relationship('User', back_populates='transcriptions')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'audio_file_path': self.audio_file_path,
            'google_drive_url': self.google_drive_url,
            'txt_document_path': self.txt_document_path,
            'md_document_path': self.md_document_path,
            'word_document_path': self.word_document_path,
            'status': self.status,
            'transcribe_prompt': self.transcribe_prompt,
            'proofread_prompt': self.proofread_prompt,
            'inference_duration': self.inference_duration,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'username': self.user.username
        }

class ErrorLog(db.Model):
    __tablename__ = 'error_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    transcription_id = db.Column(UUID(as_uuid=True), db.ForeignKey('transcriptions.id'))
    error_message = db.Column(db.Text, nullable=False)
    stack_trace = db.Column(db.Text)
    inference = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'transcription_id': self.transcription_id,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'inference': self.inference,
            'created_at': self.created_at.isoformat()
        }
    
class TranscribePrompt(db.Model):
    __tablename__ = 'transcribe_prompts'

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.Text, nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'version': self.version,
            'prompt': self.prompt,
            'created_at': self.created_at.isoformat()
        }
    
class ProofreadPrompt(db.Model):
    __tablename__ = 'proofread_prompts'

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.Text, nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'version': self.version,
            'prompt': self.prompt,
            'created_at': self.created_at.isoformat()
        }

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.Text, unique=True, nullable=False)
    setting_value = db.Column(db.Text)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
