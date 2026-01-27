from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from datetime import datetime  # ✅ Import datetime

# =====================================================
# User Model
# =====================================================

class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    
    # Relationships
    visitor_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=True)
    
    action = db.Column(db.String(50), nullable=False) # 'like', 'comment', 'follow'
    is_read = db.Column(db.Boolean, default=False)
    
    # ✅ TIMEZONE FIX: Use lambda to force new timestamp calculation on insert
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())

    visitor = db.relationship('User', foreign_keys=[visitor_id], lazy=True)
    recipient = db.relationship('User', foreign_keys=[recipient_id], lazy=True)
    post = db.relationship('Post', lazy=True)
    
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    
    # Auth Details
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
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
    
    # ✅ TIMEZONE FIX
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())
    last_login = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())
    
    # Relationships (Cascade ensures data cleanup)
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
    
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    # Flags
    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False) # Soft Delete Flag
    
    # ✅ TIMEZONE FIX
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())
    
    # Relationships with Cascades
    # cascade="all, delete-orphan" ensures comments/likes are deleted if the post is Hard Deleted
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan", passive_deletes=True)
    likes = db.relationship('Like', backref='post', cascade="all, delete-orphan", passive_deletes=True)
    
    def likes_count(self):
        return len(self.likes)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    
    # ✅ TIMEZONE FIX
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')


class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    
    is_deleted = db.Column(db.Boolean, default=False)
    
    # ✅ TIMEZONE FIX
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())
    
    likes = db.relationship('CommentLike', backref='comment', passive_deletes=True)


class Like(db.Model):
    __tablename__ = 'like'
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    
    # ✅ TIMEZONE FIX
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())


class Follow(db.Model):
    __tablename__ = 'follow'
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    # ✅ TIMEZONE FIX
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())


class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete="CASCADE"), nullable=False)
    
    # ✅ TIMEZONE FIX
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.utcnow())