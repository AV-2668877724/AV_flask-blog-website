from flask import request
from flask_login import current_user
from . import socketio, db
from .models import Message, User
from flask_socketio import emit, join_room
from datetime import datetime

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        # 1. Mark User as Online
        current_user.is_online = True
        db.session.commit()
        
        join_room(str(current_user.id))
        
        # 2. Broadcast to everyone that this user is now Online
        emit('user_status_change', {
            'user_id': current_user.id, 
            'status': 'online'
        }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        # 1. Mark User as Offline & Update Last Seen
        current_user.is_online = False
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        # 2. Broadcast to everyone that this user is now Offline
        emit('user_status_change', {
            'user_id': current_user.id, 
            'status': 'offline',
            'last_seen': current_user.last_seen.strftime("%H:%M")
        }, broadcast=True)

@socketio.on('send_message')
def handle_send_message_event(data):
    recipient_id = data.get('recipient_id')
    text = data.get('text')
    
    if not text or not recipient_id:
        return
    
    new_message = Message(
        text=text, 
        sender_id=current_user.id, 
        recipient_id=recipient_id,
        visible_to_sender=True,
        visible_to_recipient=True
    )
    db.session.add(new_message)
    db.session.commit()
    
    msg_data = {
        'id': new_message.id,
        'text': new_message.text,
        'sender_id': current_user.id,
        'time': new_message.date_created.strftime("%H:%M")
    }
    
    emit('receive_message', msg_data, room=str(recipient_id))
    emit('receive_message', msg_data, room=str(current_user.id))