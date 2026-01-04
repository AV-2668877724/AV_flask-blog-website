import re
from functools import wraps
from markupsafe import Markup
from flask import (
    Blueprint, render_template, request,
    flash, redirect, url_for,
    jsonify, abort, session
)
from flask_login import login_required, current_user

from .models import User, Post, Comment, Like
from . import db

views = Blueprint('views', __name__)

# ===============================
# ADMIN DECORATOR
# ===============================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ===============================
# ADMIN ROUTES
# ===============================

@views.route('/admin/restore-post/<int:post_id>')
@login_required
@admin_required
def admin_restore_post(post_id):
    post = Post.query.filter_by(id=post_id, is_deleted=True).first()
    if not post:
        flash('Post not found or already restored.', category='error')
        return redirect(url_for('views.home'))

    post.is_deleted = False
    db.session.commit()
    flash('Post restored successfully.', category='success')
    return redirect(url_for('views.home'))


@views.route('/admin/delete-post/<int:post_id>')
@login_required
@admin_required
def admin_delete_post(post_id):
    post = Post.query.get(post_id)
    if not post:
        flash('Post not found.', category='error')
        return redirect(url_for('views.home'))

    post.is_deleted = True
    db.session.commit()
    flash('Post deleted by admin.', category='success')
    return redirect(url_for('views.home'))


@views.route('/admin/delete-user/<int:user_id>')
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', category='error')
        return redirect(url_for('views.home'))

    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', category='success')
    return redirect(url_for('views.home'))


@views.route('/admin/delete-comment/<int:comment_id>')
@login_required
@admin_required
def admin_delete_comment(comment_id):
    comment = Comment.query.get(comment_id)
    if not comment:
        flash('Comment not found.', category='error')
        return redirect(url_for('views.home'))

    db.session.delete(comment)
    db.session.commit()
    flash('Comment deleted by admin.', category='success')
    return redirect(url_for('views.home'))

@views.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.date_created.desc()).all()

    active_posts = Post.query.filter_by(is_deleted=False) \
        .order_by(Post.date_created.desc()).all()

    deleted_posts = Post.query.filter_by(is_deleted=True) \
        .order_by(Post.date_created.desc()).all()

    comments = Comment.query.order_by(Comment.date_created.desc()).limit(50).all()

    return render_template(
        "admin_dashboard.html",
        users=users,
        active_posts=active_posts,
        deleted_posts=deleted_posts,
        comments=comments,
        user=current_user,
        is_home=False
    )


# -------------------------------------------------
# Utility helpers
# -------------------------------------------------

def enrich_posts(posts, current_user_id):
    enriched = []
    for p in posts:
        likes_count = len(p.likes)
        liked = any(l.author == current_user_id for l in p.likes)
        enriched.append({
            'id': p.id,
            'text': p.text,
            'date_created': p.date_created,
            'author': p.author,
            'user': p.user,
            'comments': p.comments,
            'likes_count': likes_count,
            'liked': liked
        })
    return enriched


def highlight(text, query):
    if not query:
        return text
    try:
        regex = re.compile(re.escape(query), re.IGNORECASE)
        return Markup(regex.sub(lambda m: f"<mark>{m.group(0)}</mark>", text))
    except Exception:
        return text


def highlight_username(username, query):
    if not query:
        return username
    try:
        regex = re.compile(re.escape(query), re.IGNORECASE)
        return Markup(regex.sub(lambda m: f"<mark>{m.group(0)}</mark>", username))
    except Exception:
        return username


# -------------------------------------------------
# MAIN ROUTES
# -------------------------------------------------

@views.route('/')
@views.route('/home')
@login_required
def home():
    page = request.args.get('page', 1, type=int)

    pagination = Post.query.filter_by(is_deleted=False) \
        .order_by(Post.date_created.desc()) \
        .paginate(page=page, per_page=5, error_out=False)

    enriched = enrich_posts(pagination.items, current_user.id)

    return render_template(
        "home.html",
        user=current_user,
        posts=enriched,
        pagination=pagination,
        is_home=True
    )


@views.route('/create-post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        text = request.form.get('text')
        if not text or not text.strip():
            flash('Post cannot be empty!', category='error')
        else:
            post = Post(text=text.strip(), author=current_user.id)
            db.session.add(post)
            db.session.commit()
            flash('Post created!', category='success')
            return redirect(url_for('views.home'))
    return render_template("create_posts.html", user=current_user, is_home=False)


@views.route('/delete-post/<id>')
@login_required
def delete_post(id):
    post = Post.query.filter_by(id=id).first()
    if not post or post.is_deleted:
        flash('Post not found!', category='error')
    elif current_user.id != post.author and not session.get('is_admin'):
        flash('You do not have permission to delete this post.', category='error')
    else:
        post.is_deleted = True
        db.session.commit()
        flash('Post deleted!', category='success')
    return redirect(url_for('views.home'))


@views.route('/edit-post/<id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Post.query.filter_by(id=id, is_deleted=False).first()
    if not post:
        flash('Post not found!', category='error')
        return redirect(url_for('views.home'))
    if current_user.id != post.author:
        flash('You do not have permission to edit this post.', category='error')
        return redirect(url_for('views.home'))

    if request.method == 'POST':
        text = request.form.get('text')
        if not text or not text.strip():
            flash('Post cannot be empty!', category='error')
        else:
            post.text = text.strip()
            db.session.commit()
            flash('Post updated!', category='success')
            return redirect(url_for('views.home'))

    return render_template("edit_post.html", user=current_user, post=post, is_home=False)


@views.route('/posts/<username>')
@login_required
def posts(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('No user with that username exists.', category='error')
        return redirect(url_for('views.home'))

    page = request.args.get('page', 1, type=int)

    pagination = Post.query.filter_by(
        author=user.id,
        is_deleted=False
    ).order_by(Post.date_created.desc()) \
     .paginate(page=page, per_page=5, error_out=False)

    enriched = enrich_posts(pagination.items, current_user.id)

    return render_template(
        "posts.html",
        user=current_user,
        posts=enriched,
        username=username,
        pagination=pagination,
        is_home=False
    )


@views.route('/create-comment/<post_id>', methods=['POST'])
@login_required
def create_comment(post_id):
    text = request.form.get('text')
    if not text or not text.strip():
        flash('Comment cannot be empty!', category='error')
    else:
        post = Post.query.filter_by(id=post_id, is_deleted=False).first()
        if not post:
            flash('Post does not exist or was deleted.', category='error')
        else:
            comment = Comment(
                text=text.strip(),
                author=current_user.id,
                post_id=post_id
            )
            db.session.add(comment)
            db.session.commit()
            flash('Comment added!', category='success')
    return redirect(url_for('views.home'))


@views.route('/delete-comment/<comment_id>')
@login_required
def delete_comment(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first()
    if not comment:
        flash('Comment not found.', category='error')
    elif current_user.id != comment.author and not session.get('is_admin'):
        flash('You do not have permission to delete this comment.', category='error')
    else:
        db.session.delete(comment)
        db.session.commit()
        flash('Comment deleted!', category='success')
    return redirect(url_for('views.home'))


@views.route('/like-post/<post_id>', methods=['POST'])
def like_post(post_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Login required'}), 401

    post = Post.query.filter_by(id=post_id, is_deleted=False).first()
    if not post:
        return jsonify({'error': 'Post no longer available'}), 410

    like = Like.query.filter_by(
        author=current_user.id,
        post_id=post_id
    ).first()

    if like:
        db.session.delete(like)
        db.session.commit()
    else:
        like = Like(author=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()

    likes_count = len(post.likes)
    liked = any(l.author == current_user.id for l in post.likes)

    return jsonify({'likes': likes_count, 'liked': liked}), 200


@views.route('/about')
def about():
    return render_template("about.html", user=current_user, is_home=False)
