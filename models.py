import os
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Database Models
class ForwardedMessage(db.Model):
    """Track all forwarded messages"""
    __tablename__ = 'forwarded_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.BigInteger, nullable=False)  # Telegram message ID
    source_chat = db.Column(db.String(255), nullable=False)
    destination_chat = db.Column(db.String(255), nullable=False)
    message_text = db.Column(db.Text, nullable=True)
    has_media = db.Column(db.Boolean, default=False)
    media_type = db.Column(db.String(50), nullable=True)  # photo, video, document, etc.
    forwarded_at = db.Column(db.DateTime, default=datetime.utcnow)
    keywords_matched = db.Column(db.String(500), nullable=True)  # Comma-separated matched keywords
    
    def to_dict(self):
        return {
            'id': self.id,
            'message_id': self.message_id,
            'source_chat': self.source_chat,
            'destination_chat': self.destination_chat,
            'message_text': self.message_text[:100] + '...' if self.message_text and len(self.message_text) > 100 else self.message_text,
            'has_media': self.has_media,
            'media_type': self.media_type,
            'forwarded_at': self.forwarded_at.isoformat(),
            'keywords_matched': self.keywords_matched
        }

class BotSession(db.Model):
    """Track bot sessions and activity"""
    __tablename__ = 'bot_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    source_chat = db.Column(db.String(255), nullable=False)
    destination_chat = db.Column(db.String(255), nullable=False)
    keywords = db.Column(db.String(1000), nullable=True)
    forward_media = db.Column(db.Boolean, default=True)
    delay_seconds = db.Column(db.Integer, default=2)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    stopped_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    messages_received = db.Column(db.Integer, default=0)
    messages_forwarded = db.Column(db.Integer, default=0)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'source_chat': self.source_chat,
            'destination_chat': self.destination_chat,
            'keywords': self.keywords,
            'forward_media': self.forward_media,
            'delay_seconds': self.delay_seconds,
            'started_at': self.started_at.isoformat(),
            'stopped_at': self.stopped_at.isoformat() if self.stopped_at else None,
            'is_active': self.is_active,
            'messages_received': self.messages_received,
            'messages_forwarded': self.messages_forwarded,
            'last_activity': self.last_activity.isoformat()
        }

class ErrorLog(db.Model):
    """Track errors and issues"""
    __tablename__ = 'error_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=True)
    error_type = db.Column(db.String(100), nullable=False)
    error_message = db.Column(db.Text, nullable=False)
    stack_trace = db.Column(db.Text, nullable=True)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'occurred_at': self.occurred_at.isoformat(),
            'resolved': self.resolved
        }

def init_database(app):
    """Initialize database with Flask app"""
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
    
    return db
