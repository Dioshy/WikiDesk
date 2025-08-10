"""
Real-time synchronization using WebSockets for LAN deployment
"""
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import current_user
from datetime import datetime
import logging
from config.deployment import NetworkConfig

logger = logging.getLogger(__name__)

class RealTimeSync:
    def __init__(self, app=None, socketio=None):
        self.app = app
        self.socketio = socketio
        self.connected_users = {}
        
        if app and socketio:
            self.init_app(app, socketio)
    
    def init_app(self, app, socketio):
        """Initialize WebSocket event handlers"""
        self.app = app
        self.socketio = socketio
        
        @socketio.on('connect')
        def handle_connect():
            if current_user.is_authenticated:
                user_id = str(current_user.id)
                self.connected_users[user_id] = {
                    'user_name': current_user.full_name,
                    'role': current_user.role,
                    'connected_at': datetime.now().isoformat(),
                    'session_id': request.sid if 'request' in globals() else None
                }
                
                # Join user to their role room
                join_room(current_user.role)
                join_room(f"user_{user_id}")
                
                logger.info(f"User {current_user.full_name} connected via WebSocket")
                
                # Notify other users
                emit('user_connected', {
                    'user_name': current_user.full_name,
                    'user_role': current_user.role,
                    'total_connected': len(self.connected_users)
                }, broadcast=True, include_self=False)
                
                # Send current user count to new connection
                emit('connection_status', {
                    'status': 'connected',
                    'connected_users': len(self.connected_users),
                    'your_role': current_user.role
                })
            else:
                logger.warning("Unauthorized WebSocket connection attempt")
                emit('connection_error', {'message': 'Authentication required'})
                return False
        
        @socketio.on('disconnect')
        def handle_disconnect():
            if current_user.is_authenticated:
                user_id = str(current_user.id)
                if user_id in self.connected_users:
                    user_info = self.connected_users.pop(user_id)
                    
                    # Leave rooms
                    leave_room(current_user.role)
                    leave_room(f"user_{user_id}")
                    
                    logger.info(f"User {current_user.full_name} disconnected")
                    
                    # Notify other users
                    emit('user_disconnected', {
                        'user_name': current_user.full_name,
                        'total_connected': len(self.connected_users)
                    }, broadcast=True)
        
        @socketio.on('entry_submitted')
        def handle_entry_submission(data):
            """Handle real-time entry submissions"""
            if current_user.is_authenticated:
                # Broadcast to all connected users except sender
                emit('new_entry_alert', {
                    'entry': data,
                    'user_name': current_user.full_name,
                    'timestamp': datetime.now().isoformat()
                }, broadcast=True, include_self=False)
                
                # Update stats for all users
                emit('stats_update_needed', {}, broadcast=True)
                
                logger.info(f"Entry broadcast from {current_user.full_name}")
        
        @socketio.on('request_stats_update')
        def handle_stats_request():
            """Handle stats update requests"""
            if current_user.is_authenticated:
                from app.models.entry import Entry
                from datetime import date
                
                # Get today's stats for requesting user
                today = date.today()
                today_entries = Entry.query.filter(
                    Entry.user_id == current_user.id,
                    Entry.date == today
                ).all()
                
                today_minutes = sum(entry.minutes for entry in today_entries)
                today_calls = len(today_entries)
                
                emit('stats_updated', {
                    'today_minutes': today_minutes,
                    'today_calls': today_calls,
                    'last_update': datetime.now().isoformat()
                })
        
        @socketio.on('ping')
        def handle_ping():
            """Handle ping/pong for connection monitoring"""
            emit('pong')
        
        @socketio.on('admin_broadcast')
        def handle_admin_broadcast(data):
            """Handle admin broadcasts"""
            if current_user.is_authenticated and current_user.is_admin():
                emit('admin_message', {
                    'message': data.get('message'),
                    'from': current_user.full_name,
                    'timestamp': datetime.now().isoformat()
                }, broadcast=True, include_self=False)
                
                logger.info(f"Admin broadcast from {current_user.full_name}")
        
        @socketio.on('sync_request')
        def handle_sync_request():
            """Handle offline sync requests"""
            if current_user.is_authenticated:
                from app.database_manager import db_manager
                
                synced_count = db_manager.sync_offline_entries(app)
                
                emit('sync_completed', {
                    'synced_count': synced_count,
                    'timestamp': datetime.now().isoformat()
                })
                
                if synced_count > 0:
                    # Notify all users that data was synced
                    emit('data_synced', {
                        'user': current_user.full_name,
                        'count': synced_count
                    }, broadcast=True, include_self=False)
    
    def broadcast_entry_update(self, entry_data, action='created'):
        """Broadcast entry updates to all connected clients"""
        if self.socketio:
            self.socketio.emit('entry_updated', {
                'action': action,
                'entry': entry_data,
                'timestamp': datetime.now().isoformat()
            })
    
    def broadcast_user_stats_update(self, user_id):
        """Broadcast stats update for specific user"""
        if self.socketio:
            self.socketio.emit('user_stats_changed', {
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }, room=f"user_{user_id}")
    
    def broadcast_system_message(self, message, message_type='info'):
        """Broadcast system messages to all users"""
        if self.socketio:
            self.socketio.emit('system_message', {
                'message': message,
                'type': message_type,
                'timestamp': datetime.now().isoformat()
            })
    
    def get_connected_users_count(self):
        """Get number of connected users"""
        return len(self.connected_users)
    
    def get_connected_users_info(self):
        """Get detailed info about connected users"""
        return self.connected_users.copy()

# Global real-time sync instance
realtime_sync = RealTimeSync()