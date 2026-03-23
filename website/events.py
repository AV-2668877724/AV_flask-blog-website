from flask import request
from flask_login import current_user
from . import socketio, db
from .models import Message, User, Notification # 🚀 ADDED Notification model
from flask_socketio import emit, join_room, leave_room
from datetime import datetime
import bleach # 🚀 FIX 1: Import bleach for XSS protection

# 🚀 IMPORT THE PROCESSOR FROM VIEWS FOR LINK PREVIEWS & TAGS
from .views import process_text_links

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
    raw_text = data.get('text', '').strip()
    
    if not raw_text or not recipient_id: return
    
    # 🚀 FIX 5: Validate recipient exists (IDOR Prevention)
    recipient = User.query.get(recipient_id)
    if not recipient: return

    # 🚀 FIX 1: Sanitize chat input (XSS Prevention)
    # We strip all HTML tags from chat to ensure no malicious scripts are executed
    clean_text = bleach.clean(raw_text, tags=[], attributes={}, strip=True)
    if not clean_text: return # Prevent sending empty messages if they only typed HTML
    
    # 🚀 NEW: Generate Link Previews, Mentions, and Hashtags!
    final_text = process_text_links(clean_text)
    
    # 1. Save to Database
    new_message = Message(
        text=final_text, 
        sender_id=current_user.id, 
        recipient_id=recipient_id,
        visible_to_sender=True,
        visible_to_recipient=True,
        date_created=datetime.utcnow()
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    # ==========================================
    # 🚀 NEW: Create Notification for the Message
    # ==========================================
    existing_notif = Notification.query.filter_by(
        visitor_id=current_user.id, 
        recipient_id=recipient_id, 
        action='message', 
        is_read=False
    ).first()
    
    if not existing_notif:
        notif = Notification(
            visitor_id=current_user.id, 
            recipient_id=recipient_id, 
            action='message', 
            date_created=datetime.utcnow()
        )
        db.session.add(notif)
        db.session.commit()
    
    # 2. Prepare Payload
    msg_data = {
        'id': new_message.id,
        'text': new_message.text,
        'sender_id': current_user.id,
        'sender_username': current_user.username, # 🚀 NEW: Send the username to the frontend!
        'recipient_id': recipient_id,
        'time': new_message.date_created.isoformat() + 'Z' 
    }
    
    # 3. Emit to both parties
    # Send to Recipient (Room)
    emit('receive_message', msg_data, room=str(recipient_id))
    
    # Send to Sender's Other Tabs (Room)
    emit('receive_message', msg_data, room=str(current_user.id))
    
    # Send to Sender's Current Tab (Direct Reply)
    emit('receive_message', msg_data)
    
@socketio.on('typing')
def handle_typing(data):
    if not current_user.is_authenticated: return
    
    recipient_id = data.get('recipient_id')
    is_typing = data.get('is_typing', False)
    
    if not recipient_id: return
    
    # Broadcast the typing status strictly to the recipient's private room
    emit('user_typing', {
        'user_id': current_user.id,
        'is_typing': is_typing
    }, room=str(recipient_id))
    
@socketio.on('chat_opened')
def handle_chat_opened(data):
    if not current_user.is_authenticated: return
    sender_id = data.get('sender_id')
    
    if sender_id:
        # Tell the sender that current_user has opened the chat, so turn all ticks blue!
        emit('all_messages_read', {'reader_id': current_user.id}, room=str(sender_id))

@socketio.on('message_read')
def handle_message_read(data):
    if not current_user.is_authenticated: return
    msg_id = data.get('msg_id')
    sender_id = data.get('sender_id')
    
    if msg_id and sender_id:
        msg = Message.query.get(msg_id)
        # Ensure we are the recipient of this message before marking it read
        if msg and msg.recipient_id == current_user.id:
            msg.is_read = True
            db.session.commit()
            # Tell the sender to turn this specific tick blue
            emit('single_message_read', {'msg_id': msg_id, 'reader_id': current_user.id}, room=str(sender_id))