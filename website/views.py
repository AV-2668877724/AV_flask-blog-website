import re
from difflib import get_close_matches
from markupsafe import Markup
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from .models import Like, Post, User, Comment
from . import db

views = Blueprint('views', __name__)

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
    """Wrap matching query terms in <mark> tags for highlighting."""
    if not query:
        return text
    try:
        regex = re.compile(re.escape(query), re.IGNORECASE)
        return Markup(regex.sub(lambda m: f"<mark>{m.group(0)}</mark>", text))
    except Exception:
        return text

def highlight_username(username, query):
    """Highlight query inside username if present."""
    if not query:
        return username
    try:
        regex = re.compile(re.escape(query), re.IGNORECASE)
        return Markup(regex.sub(lambda m: f"<mark>{m.group(0)}</mark>", username))
    except Exception:
        return username

@views.route('/')
@views.route('/home')
@login_required
def home():
    posts = Post.query.order_by(Post.date_created.desc()).all()
    enriched = enrich_posts(posts, current_user.id)
    return render_template("home.html", user=current_user, posts=enriched, is_home=True)

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
    if not post:
        flash('Post not found!', category='error')
    elif current_user.id != post.author:
        flash('You do not have permission to delete this post.', category='error')
    else:
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted!', category='success')
    return redirect(url_for('views.home'))

@views.route('/edit-post/<id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Post.query.filter_by(id=id).first()
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
    posts = user.posts
    enriched = enrich_posts(posts, current_user.id)
    return render_template("posts.html", user=current_user, posts=enriched, username=username, is_home=False)

@views.route('/create-comment/<post_id>', methods=['POST'])
@login_required
def create_comment(post_id):
    text = request.form.get('text')
    if not text or not text.strip():
        flash('Comment cannot be empty!', category='error')
    else:
        post = Post.query.filter_by(id=post_id).first()
        if not post:
            flash('Post does not exist.', category='error')
        else:
            comment = Comment(text=text.strip(), author=current_user.id, post_id=post_id)
            db.session.add(comment)
            db.session.commit()
            flash('Comment added!', category='success')
    return redirect(url_for('views.home'))

@views.route('/delete-comment/<comment_id>')
@login_required
def delete_comment(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first()
    if not comment:
        flash('Comment not found!', category='error')
    elif current_user.id != comment.author:
        flash('You do not have permission to delete this comment.', category='error')
    else:
        db.session.delete(comment)
        db.session.commit()
        flash('Comment deleted!', category='success')
    return redirect(url_for('views.home'))

@views.route('/like-post/<post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if not post:
        return jsonify({'error': "Post does not exist"}), 404

    like = Like.query.filter_by(author=current_user.id, post_id=post_id).first()
    if like:
        db.session.delete(like)
        db.session.commit()
    else:
        like = Like(author=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()

    # Refresh post to get updated likes
    post = Post.query.filter_by(id=post_id).first()
    likes_count = len(post.likes)
    liked = any(l.author == current_user.id for l in post.likes)
    return jsonify({'likes': likes_count, 'liked': liked}), 200

@views.route('/about')
def about():
    return render_template("about.html", user=current_user, is_home=False)

@views.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'users': [], 'posts': []})
    
    # Search users
    users = User.query.filter(User.username.like(f'%{query}%')).limit(5).all()
    user_results = [{'username': u.username, 'id': u.id} for u in users]
    
    # Always search posts
    posts = Post.query.filter(Post.text.like(f'%{query}%')).limit(5).all()
    post_results = [{'id': p.id, 'text': p.text[:100] + '...' if len(p.text) > 100 else p.text, 'author': p.user.username} for p in posts]
    
    return jsonify({'users': user_results, 'posts': post_results})

@views.route('/search-page')
@login_required
def search_page():
    query = request.args.get('q', '').strip()
    if not query:
        flash('No search query provided.', category='error')
        return redirect(url_for('views.home'))
    
    # Search users
    users = User.query.filter(User.username.like(f'%{query}%')).limit(5).all()
    
    # Search posts
    posts = Post.query.filter(Post.text.like(f'%{query}%')).limit(10).all()
    if not posts:
        # If no posts match, show recent posts as suggestions
        posts = Post.query.order_by(Post.date_created.desc()).limit(10).all()
    enriched_posts = enrich_posts(posts, current_user.id)
    
    return render_template("search.html", query=query, users=users, posts=enriched_posts, user=current_user, is_home=False)
