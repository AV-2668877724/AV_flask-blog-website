from flask import request
from flask_login import current_user
from . import socketio, db
from .models import Message, User
from flask_socketio import emit, join_room, leave_room
from datetime import datetime

# ==================================================
# SOCKET.IO EVENT HANDLERS
# ==================================================

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        # 1. Mark User as Online
        current_user.is_online = True
        db.session.commit()
        
        # 2. Join a private room
        join_room(str(current_user.id))
        
        # 3. Broadcast status
        emit('user_status_change', {
            'user_id': current_user.id, 
            'status': 'online'
        }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        # 1. Mark User as Offline
        current_user.is_online = False
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        # 2. Leave room
        leave_room(str(current_user.id))
        
        # 3. Broadcast status
        emit('user_status_change', {
            'user_id': current_user.id, 
            'status': 'offline',
            'last_seen': current_user.last_seen.strftime("%H:%M")
        }, broadcast=True)

@socketio.on('send_message')
def handle_send_message_event(data):
    if not current_user.is_authenticated: return

    recipient_id = data.get('recipient_id')
    text = data.get('text', '').strip()
    
    if not text or not recipient_id: return
    
    # 1. Save to Database
    new_message = Message(
        text=text, 
        sender_id=current_user.id, 
        recipient_id=recipient_id,
        visible_to_sender=True,
        visible_to_recipient=True,
        date_created=datetime.utcnow()
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    # 2. Prepare Payload
    msg_data = {
        'id': new_message.id,
        'text': new_message.text,
        'sender_id': current_user.id,
        'recipient_id': recipient_id,
        'time': new_message.date_created.strftime("%H:%M")
    }
    
    # 3. Emit to both parties
    # Send to Recipient (Room)
    emit('receive_message', msg_data, room=str(recipient_id))
    
    # Send to Sender's Other Tabs (Room)
    emit('receive_message', msg_data, room=str(current_user.id))
    
    # ✅ FIX: Send to Sender's Current Tab (Direct Reply)
    # This ensures the user sees the message immediately even if room joining failed
    emit('receive_message', msg_data)