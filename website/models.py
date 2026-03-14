from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from datetime import datetime
from sqlalchemy import Index  # ✅ NEW: Imported Index for performance

# =====================================================
# Notification Model
# =====================================================

class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    
    # Relationships
    visitor_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    # Single Index (Keep this for general lookups)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=True)
    
    action = db.Column(db.String(50), nullable=False) # 'like', 'comment', 'follow'
    is_read = db.Column(db.Boolean, default=False, index=True)
    
    # Single Index (Faster sorting)
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow(), index=True)

    visitor = db.relationship('User', foreign_keys=[visitor_id], lazy=True)
    recipient = db.relationship('User', foreign_keys=[recipient_id], lazy=True)
    post = db.relationship('Post', lazy=True)

    # ⚡ PERFORMANCE: Composite Index
    # This allows the DB to instantly count unread notifications for a specific user
    # without scanning the whole table.
    __table_args__ = (
        Index('idx_notif_recipient_read', 'recipient_id', 'is_read'),
    )

# =====================================================
# User Model
# =====================================================

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    
    # Auth Details (Indexed for fast login)
    username = db.Column(db.String(150), unique=True, index=True)
    email = db.Column(db.String(150), unique=True, index=True)
    password = db.Column(db.String(150), nullable=False)
    
    # Profile Details
    profile_pic = db.Column(db.String(150), nullable=True)
    cover_pic = db.Column(db.String(150), nullable=True)
    bio = db.Column(db.String(300), default="")
    social_links = db.Column(JSON, default=dict)
    
    # Status Flags
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    deactivation_reason = db.Column(db.String(500), nullable=True)
    
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())
    last_login = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())
    
    # Online Status
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())
    
    # Relationships
    posts = db.relationship('Post', backref='user', passive_deletes=True)
    comments = db.relationship('Comment', backref='user', passive_deletes=True)
    likes = db.relationship('Like', backref='user', passive_deletes=True)
    
# =====================================================
# Post Model
# =====================================================

class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    cover_image = db.Column(db.String(150), nullable=True)
    
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Flags
    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Index for the Home Feed sorting
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow(), index=True)    
    
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan", passive_deletes=True)
    likes = db.relationship('Like', backref='post', cascade="all, delete-orphan", passive_deletes=True)
    
    def likes_count(self):
        return len(self.likes)

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    
    text = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow(), index=True)    
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

    visible_to_sender = db.Column(db.Boolean, default=True)
    visible_to_recipient = db.Column(db.Boolean, default=True)

    # ⚡ PERFORMANCE: Composite Index
    # Instant lookup for "Unread Messages for User X"
    __table_args__ = (
        Index('idx_msg_recipient_read', 'recipient_id', 'is_read'),
    )
    
class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False, index=True)
    
    is_deleted = db.Column(db.Boolean, default=False)
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow(), index=True)
    
    likes = db.relationship('CommentLike', backref='comment', passive_deletes=True)

class Like(db.Model):
    __tablename__ = 'like'
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())

class Follow(db.Model):
    __tablename__ = 'follow'
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    following_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())

class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete="CASCADE"), nullable=False, index=True)
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())