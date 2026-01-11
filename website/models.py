from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy.types import JSON


# =====================================================
# User Model
# =====================================================

class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    bio = db.Column(db.String(300), default="")
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())

    # 🔐 Security question hashes
    dob_hash = db.Column(db.String(150))
    fav_person_hash = db.Column(db.String(150))

    
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
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())

    author = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )

    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    comments = db.relationship('Comment', backref='post', passive_deletes=True)
    likes = db.relationship('Like', backref='post', passive_deletes=True)


# =====================================================
# Comment Model
# =====================================================

class Comment(db.Model):
    __tablename__ = 'comment'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())

    author = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )

    post_id = db.Column(
        db.Integer,
        db.ForeignKey('post.id', ondelete='CASCADE'),
        nullable=False
    )

    is_deleted = db.Column(db.Boolean, default=False)


# =====================================================
# Like Model
# =====================================================

class Like(db.Model):
    __tablename__ = 'like'

    id = db.Column(db.Integer, primary_key=True)

    author = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )

    post_id = db.Column(
        db.Integer,
        db.ForeignKey('post.id', ondelete='CASCADE'),
        nullable=False
    )

    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
