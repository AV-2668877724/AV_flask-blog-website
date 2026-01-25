from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

# =====================================================
# User Model
# =====================================================

class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    
    # Who triggered it? (e.g., The person who Liked your post)
    visitor_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    # Who receives it? (You)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    # What happened? ('like', 'comment', 'follow')
    action = db.Column(db.String(50), nullable=False)
    
    # Which post? (Optional, null if it's a follow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=True)
    
    is_read = db.Column(db.Boolean, default=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())

    # Relationships (for easy access in templates)
    visitor = db.relationship('User', foreign_keys=[visitor_id], lazy=True)
    recipient = db.relationship('User', foreign_keys=[recipient_id], lazy=True)
    post = db.relationship('Post', lazy=True)
    
class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    # ✅ NEW: Profile Picture Column
    profile_pic = db.Column(db.String(150), nullable=True)
    cover_pic = db.Column(db.String(150), nullable=True)

    bio = db.Column(db.String(300), default="")
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    is_verified = db.Column(db.Boolean, default=False)
    deactivation_reason = db.Column(db.String(500), nullable=True)

    social_links = db.Column(JSON, default=dict)

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
    
    # ✅ NEW: Cover Image Column
    cover_image = db.Column(db.String(150), nullable=True)
    
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    is_deleted = db.Column(db.Boolean, default=False)
    author = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )

    comments = db.relationship('Comment', backref='post', passive_deletes=True)
    likes = db.relationship('Like', backref='post', passive_deletes=True)

# ... (Keep Comment, Like, and Follow models as they were) ...
class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)

class Like(db.Model):
    __tablename__ = 'like'
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())

class Follow(db.Model):
    __tablename__ = 'follow'
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())