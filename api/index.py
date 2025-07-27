#!/usr/bin/env python3
"""
Telegram Autoforward Bot for Vercel
24/7 automatic message forwarding with web dashboard and database logging
"""

import os
import asyncio
import json
import logging
import traceback
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import threading
import time

# Add current directory to path for imports
sys.path.append('.')
from models import db, init_database, ForwardedMessage, BotSession, ErrorLog

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'telegram_autoforward_vercel_2025')

# Initialize database
try:
    database = init_database(app)
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    database = None

# Global bot instance
bot_instance = None
bot_thread = None
bot_running = False

class TelegramAutoForwarder:
    """Telegram autoforward bot for 24/7 operation with database logging"""
    
    def __init__(self):
        # Get environment variables with proper type conversion
        api_id_str = os.getenv('TELEGRAM_API_ID')
        self.api_id = int(api_id_str) if api_id_str else None
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.phone = os.getenv('TELEGRAM_PHONE')
        self.source_chat = os.getenv('SOURCE_CHAT')
        self.destination_chat = os.getenv('DESTINATION_CHAT')
        self.keywords = self._parse_keywords(os.getenv('KEYWORDS', ''))
        self.forward_media = os.getenv('FORWARD_MEDIA', 'true').lower() == 'true'
        
        delay_str = os.getenv('DELAY_SECONDS', '2')
        self.delay_seconds = int(delay_str) if delay_str.isdigit() else 2
        
        self.client = None
        self.authenticated = False
        self.running = False
        self.session_id = f"bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.db_session = None
        self.stats = {
            'messages_received': 0,
            'messages_forwarded': 0,
            'last_message_time': None,
            'start_time': None,
            'errors': []
        }
        
    def _parse_keywords(self, keywords_str: str) -> List[str]:
        """Parse keywords from environment variable"""
        if not keywords_str:
            return []
        return [k.strip() for k in keywords_str.split(',') if k.strip()]
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize Telegram client and authenticate"""
        try:
            if not all([self.api_id, self.api_hash, self.phone]):
                return {
                    'success': False,
                    'error': 'Missing required environment variables: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE'
                }
            
            from telethon import TelegramClient
            from telethon.errors import SessionPasswordNeededError
            
            # Use session file for persistence - check multiple locations
            session_paths = [
                'telegram_session',  # Local development
                './telegram_session',  # Vercel function root
                '/tmp/telegram_session'  # Fallback
            ]
            
            session_file = None
            for path in session_paths:
                if os.path.exists(f"{path}.session"):
                    session_file = path
                    break
            
            if not session_file:
                session_file = session_paths[0]  # Default to first path
            
            self.client = TelegramClient(session_file, self.api_id, self.api_hash)
            
            await self.client.start(phone=self.phone)
            
            if await self.client.is_user_authorized():
                self.authenticated = True
                logger.info("Successfully authenticated with existing session")
                return {
                    'success': True,
                    'message': 'Successfully authenticated with existing session'
                }
            else:
                return {
                    'success': False,
                    'error': 'Session expired or invalid. Run setup_auth.py to re-authenticate.'
                }
                
        except Exception as e:
            error_msg = f"Failed to initialize Telegram client: {str(e)}"
            logger.error(error_msg)
            await self._log_error("initialization", error_msg, traceback.format_exc())
            return {
                'success': False,
                'error': error_msg
            }
    
    async def start_forwarding(self) -> Dict[str, Any]:
        """Start the message forwarding process"""
        try:
            if not self.client or not self.authenticated:
                init_result = await self.initialize()
                if not init_result['success']:
                    return init_result
            
            if not all([self.source_chat, self.destination_chat]):
                return {
                    'success': False,
                    'error': 'SOURCE_CHAT and DESTINATION_CHAT must be configured'
                }
            
            from telethon import events
            from telethon.errors import FloodWaitError
            
            # Get chat entities
            try:
                source_entity = await self.client.get_entity(self.source_chat)
                dest_entity = await self.client.get_entity(self.destination_chat)
                logger.info(f"Successfully connected to chats: {self.source_chat} -> {self.destination_chat}")
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Failed to get chat entities: {str(e)}',
                    'details': 'Check SOURCE_CHAT and DESTINATION_CHAT environment variables'
                }
            
            @self.client.on(events.NewMessage(chats=source_entity))
            async def message_handler(event):
                try:
                    self.stats['messages_received'] += 1
                    self.stats['last_message_time'] = datetime.now().isoformat()
                    
                    message_text = event.message.text or ''
                    
                    # Apply keyword filter
                    should_forward = True
                    if self.keywords:
                        should_forward = any(keyword.lower() in message_text.lower() 
                                           for keyword in self.keywords)
                    
                    if should_forward:
                        # Add delay to avoid rate limits
                        if self.delay_seconds > 0:
                            await asyncio.sleep(self.delay_seconds)
                        
                        # Forward the message
                        if self.client:
                            if self.forward_media and event.message.media:
                                await self.client.forward_messages(dest_entity, event.message)
                            elif not event.message.media:
                                await self.client.forward_messages(dest_entity, event.message)
                            
                            self.stats['messages_forwarded'] += 1
                            
                            # Log to database
                            await self._log_forwarded_message(event, should_forward)
                            
                            logger.info(f"Forwarded message from {self.source_chat} to {self.destination_chat}")
                    
                except Exception as e:
                    error_msg = f"Error forwarding message: {str(e)}"
                    logger.error(error_msg)
                    await self._log_error("forwarding", error_msg, traceback.format_exc())
                    self.stats['errors'].append({
                        'time': datetime.now().isoformat(),
                        'error': error_msg
                    })
            
            self.running = True
            self.stats['start_time'] = datetime.now().isoformat()
            
            # Save session to database
            await self._create_db_session()
            
            logger.info(f"Started forwarding from {self.source_chat} to {self.destination_chat}")
            
            # Keep the client running
            if self.client:
                await self.client.run_until_disconnected()
            
            return {
                'success': True,
                'message': 'Forwarding started successfully',
                'config': {
                    'source_chat': self.source_chat,
                    'destination_chat': self.destination_chat,
                    'keywords': self.keywords,
                    'forward_media': self.forward_media,
                    'delay_seconds': self.delay_seconds
                }
            }
            
        except Exception as e:
            error_msg = f"Failed to start forwarding: {str(e)}"
            logger.error(error_msg)
            await self._log_error("startup", error_msg, traceback.format_exc())
            return {
                'success': False,
                'error': error_msg
            }
    
    async def _create_db_session(self):
        """Create database session record"""
        try:
            if database:
                with app.app_context():
                    self.db_session = BotSession(
                        session_id=self.session_id,
                        source_chat=self.source_chat,
                        destination_chat=self.destination_chat,
                        keywords=','.join(self.keywords) if self.keywords else None,
                        forward_media=self.forward_media,
                        delay_seconds=self.delay_seconds,
                        started_at=datetime.utcnow(),
                        is_active=True
                    )
                    db.session.add(self.db_session)
                    db.session.commit()
        except Exception as e:
            logger.error(f"Failed to create database session: {e}")

    async def _log_forwarded_message(self, event, matched_keywords=None):
        """Log forwarded message to database"""
        try:
            if database:
                with app.app_context():
                    message_text = event.message.text or ''
                    media_type = None
                    if event.message.media:
                        media_type = type(event.message.media).__name__
                    
                    matched_kw = None
                    if matched_keywords and self.keywords:
                        matched = [kw for kw in self.keywords if kw.lower() in message_text.lower()]
                        if matched:
                            matched_kw = ','.join(matched)
                    
                    forwarded_msg = ForwardedMessage(
                        message_id=event.message.id,
                        source_chat=self.source_chat,
                        destination_chat=self.destination_chat,
                        message_text=message_text[:1000],  # Truncate for storage
                        has_media=bool(event.message.media),
                        media_type=media_type,
                        keywords_matched=matched_kw,
                        forwarded_at=datetime.utcnow()
                    )
                    db.session.add(forwarded_msg)
                    
                    # Update session stats
                    if self.db_session:
                        self.db_session.messages_forwarded += 1
                        self.db_session.last_activity = datetime.utcnow()
                    
                    db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log forwarded message: {e}")

    async def _log_error(self, error_type, error_message, stack_trace=None):
        """Log error to database"""
        try:
            if database:
                with app.app_context():
                    error_log = ErrorLog(
                        session_id=self.session_id,
                        error_type=error_type,
                        error_message=str(error_message),
                        stack_trace=stack_trace,
                        occurred_at=datetime.utcnow()
                    )
                    db.session.add(error_log)
                    db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}")

    async def stop_forwarding(self):
        """Stop the forwarding process"""
        self.running = False
        
        # Update database session
        try:
            if database and self.db_session:
                with app.app_context():
                    self.db_session.stopped_at = datetime.utcnow()
                    self.db_session.is_active = False
                    db.session.commit()
        except Exception as e:
            logger.error(f"Failed to update database session: {e}")
        
        if self.client:
            await self.client.disconnect()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return {
            'running': self.running,
            'authenticated': self.authenticated,
            'stats': self.stats,
            'config': {
                'source_chat': self.source_chat,
                'destination_chat': self.destination_chat,
                'keywords': self.keywords,
                'forward_media': self.forward_media,
                'delay_seconds': self.delay_seconds
            }
        }

def run_bot_async():
    """Run bot in asyncio loop"""
    global bot_instance, bot_running
    
    async def main():
        global bot_running
        try:
            bot_instance = TelegramAutoForwarder()
            bot_running = True
            result = await bot_instance.start_forwarding()
            logger.info(f"Bot result: {result}")
        except Exception as e:
            logger.error(f"Bot error: {e}")
            bot_running = False
    
    asyncio.run(main())

# Flask routes
@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/status')
def status():
    """Get bot status and statistics"""
    global bot_instance, bot_running
    
    if bot_instance:
        return jsonify(bot_instance.get_stats())
    else:
        return jsonify({
            'running': False,
            'authenticated': False,
            'message': 'Bot not initialized'
        })

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the forwarding bot"""
    global bot_thread, bot_running
    
    if bot_running:
        return jsonify({
            'success': False,
            'error': 'Bot is already running'
        })
    
    # Start bot in separate thread
    bot_thread = threading.Thread(target=run_bot_async, daemon=True)
    bot_thread.start()
    
    # Wait a moment for initialization
    time.sleep(2)
    
    return jsonify({
        'success': True,
        'message': 'Bot start initiated. Check status for details.'
    })

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the forwarding bot"""
    global bot_instance, bot_running
    
    if bot_instance:
        asyncio.run(bot_instance.stop_forwarding())
    
    bot_running = False
    
    return jsonify({
        'success': True,
        'message': 'Bot stopped successfully'
    })

@app.route('/api/config')
def get_config():
    """Get current configuration"""
    return jsonify({
        'api_id': os.getenv('TELEGRAM_API_ID', 'Not set'),
        'phone': os.getenv('TELEGRAM_PHONE', 'Not set'),
        'source_chat': os.getenv('SOURCE_CHAT', 'Not set'),
        'destination_chat': os.getenv('DESTINATION_CHAT', 'Not set'),
        'keywords': os.getenv('KEYWORDS', 'None'),
        'forward_media': os.getenv('FORWARD_MEDIA', 'true'),
        'delay_seconds': os.getenv('DELAY_SECONDS', '2')
    })

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'bot_running': bot_running
    })

# Database API endpoints
@app.route('/api/database/messages')
def get_forwarded_messages():
    """Get recent forwarded messages from database"""
    try:
        if not database:
            return jsonify({'error': 'Database not available'}), 500
        
        limit = request.args.get('limit', 50, type=int)
        messages = ForwardedMessage.query.order_by(ForwardedMessage.forwarded_at.desc()).limit(limit).all()
        
        return jsonify({
            'messages': [msg.to_dict() for msg in messages],
            'total': len(messages)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/sessions')
def get_bot_sessions():
    """Get bot sessions from database"""
    try:
        if not database:
            return jsonify({'error': 'Database not available'}), 500
        
        sessions = BotSession.query.order_by(BotSession.started_at.desc()).limit(20).all()
        
        return jsonify({
            'sessions': [session.to_dict() for session in sessions],
            'total': len(sessions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/errors')
def get_error_logs():
    """Get error logs from database"""
    try:
        if not database:
            return jsonify({'error': 'Database not available'}), 500
        
        errors = ErrorLog.query.order_by(ErrorLog.occurred_at.desc()).limit(30).all()
        
        return jsonify({
            'errors': [error.to_dict() for error in errors],
            'total': len(errors)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/stats')
def get_database_stats():
    """Get overall statistics from database"""
    try:
        if not database:
            return jsonify({'error': 'Database not available'}), 500
        
        total_messages = ForwardedMessage.query.count()
        total_sessions = BotSession.query.count()
        active_sessions = BotSession.query.filter_by(is_active=True).count()
        total_errors = ErrorLog.query.count()
        unresolved_errors = ErrorLog.query.filter_by(resolved=False).count()
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_messages = ForwardedMessage.query.filter(
            ForwardedMessage.forwarded_at >= yesterday
        ).count()
        
        return jsonify({
            'total_messages_forwarded': total_messages,
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_errors': total_errors,
            'unresolved_errors': unresolved_errors,
            'messages_last_24h': recent_messages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Auto-start bot if all environment variables are set
def auto_start_bot():
    """Auto-start bot if configuration is complete"""
    required_vars = ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH', 'TELEGRAM_PHONE', 'SOURCE_CHAT', 'DESTINATION_CHAT']
    
    if all(os.getenv(var) for var in required_vars):
        logger.info("Auto-starting bot with environment configuration...")
        start_bot()
    else:
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        logger.info(f"Auto-start disabled. Missing environment variables: {missing_vars}")

# Initialize auto-start
auto_start_bot()

# For Vercel serverless function
def handler(request, start_response):
    return app(request, start_response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
