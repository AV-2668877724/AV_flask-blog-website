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

@views.route('/')
@views.route('/home')
@login_required
def home():
    posts = Post.query.order_by(Post.date_created.desc()).all()
    enriched = enrich_posts(posts, current_user.id)
    return render_template("home.html", user=current_user, posts=enriched)

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
    return render_template("create_posts.html", user=current_user)

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

@views.route('/posts/<username>')
@login_required
def posts(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('No user with that username exists.', category='error')
        return redirect(url_for('views.home'))
    posts = user.posts
    enriched = enrich_posts(posts, current_user.id)
    return render_template("posts.html", user=current_user, posts=enriched, username=username)

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
    # No login required; show public about page
    return render_template("about.html", user=current_user)

