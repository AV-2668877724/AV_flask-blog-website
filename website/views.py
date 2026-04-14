from functools import wraps
from flask import ( 
    Blueprint, render_template, request,
    flash, redirect, url_for, abort, jsonify, current_app, make_response,redirect
)
from flask_login import login_required, current_user, logout_user
from .models import User, Post, Comment, Like, Follow, Notification, CommentLike, Message, SavedPost, Block, Report
from sqlalchemy.exc import IntegrityError

from . import db, limiter
from datetime import datetime, timezone
from sqlalchemy import func, or_, desc, and_
from werkzeug.security import check_password_hash
from sqlalchemy.orm import joinedload, subqueryload 
import re, json, os
from sqlalchemy.orm.attributes import flag_modified
import secrets
from flask_socketio import emit, join_room, leave_room
import bleach 

import requests
from bs4 import BeautifulSoup

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# 🚀 NEW: Import all helpers from our new utils file
from .utils import (
    get_block_lists, sanitize_html, process_text_links, notify_mentions, 
    allowed_file, upload_to_cloudinary, delete_from_cloudinary, 
    enrich_posts, create_notification, detect_platform
)

views = Blueprint('views', __name__)

# =================================================
# MAIN ROUTES
# =================================================

@views.route('/home')
@views.route('/')
@login_required
def home():
    page = request.args.get('page', 1, type=int)
    blockers, blocked_by_me = get_block_lists(current_user.id) 
    all_blocked_ids = list(set(blockers + blocked_by_me))
    
    pagination = Post.query.options(
        joinedload(Post.user),
        subqueryload(Post.likes),
        subqueryload(Post.comments).joinedload(Comment.user)
    ).filter(
        Post.is_deleted == False,
        ~Post.author.in_(all_blocked_ids) if all_blocked_ids else True
    ).order_by(desc(Post.date_created)).paginate(page=page, per_page=10, error_out=False)

    posts = enrich_posts(pagination.items, all_blocked_ids)

    # 🚀 NEW: Handle Infinite Scroll AJAX Requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'html': render_template('_posts.html', posts=posts, user=current_user),
            'has_next': pagination.has_next
        })

    return render_template("home.html", user=current_user, posts=posts, pagination=pagination)


@views.route('/create-post', methods=['GET', 'POST'])
@login_required
@limiter.limit("5 per minute")
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        excerpt = request.form.get('excerpt')
        raw_text = request.form.get('text')
        cover_image_file = request.files.get('cover_image')
        cover_image_url = None

        if not raw_text or not title:
            flash('Title and Post content cannot be empty!', category='error')
        else:
            clean_text = sanitize_html(raw_text)
            final_text = process_text_links(clean_text)
            
            # 🚀 NEW: Calculate Read Time & Generate Slug
            word_count = len(re.findall(r'\w+', clean_text))
            read_time = max(1, round(word_count / 200))
            
            base_slug = re.sub(r'[^\w\s-]', '', title.lower()).strip()
            base_slug = re.sub(r'[-\s]+', '-', base_slug)
            slug = f"{base_slug}-{secrets.token_hex(4)}"
            
            if cover_image_file and cover_image_file.filename != '':
                cover_image_url = upload_to_cloudinary(cover_image_file, 'posts', width=1080)
            
            # Since you updated models.py with default datetime.now, 
            # we can safely drop date_created from here.
            post = Post(
                title=title,
                slug=slug,
                excerpt=excerpt,
                read_time=read_time,
                text=final_text, 
                author=current_user.id, 
                cover_image=cover_image_url
            )
            
            db.session.add(post)
            db.session.commit()
            
            notify_mentions(raw_text, post.id, current_user.id)
            
            flash('Post created successfully!', category='success')
            return redirect(url_for('views.home'))

    return render_template('create_posts.html', user=current_user)


@views.route("/edit-post/<int:id>", methods=['GET', 'POST'])
@login_required
@limiter.limit("10 per minute")
def edit_post(id):
    post = Post.query.get_or_404(id)

    if current_user.id != post.author:
        flash("You cannot edit this post.", category='error')
        return redirect(url_for('views.home'))

    if request.method == "POST":
        title = request.form.get('title')
        excerpt = request.form.get('excerpt')
        raw_text = request.form.get('text')
        file = request.files.get('cover_image') 
        
        if not raw_text or not title:
            flash("Title and Post content cannot be empty.", category='error')
        else:
            clean_text = sanitize_html(raw_text)
            post.text = process_text_links(clean_text)
            
            # 🚀 NEW: Update new fields
            post.title = title
            post.excerpt = excerpt
            
            word_count = len(re.findall(r'\w+', clean_text))
            post.read_time = max(1, round(word_count / 200))
            
            # Update slug only if title changed to preserve old links
            base_slug = re.sub(r'[^\w\s-]', '', title.lower()).strip()
            base_slug = re.sub(r'[-\s]+', '-', base_slug)
            
            # Ensure we only append a new hex if the slug base actually changed
            if not post.slug or not post.slug.startswith(base_slug):
                post.slug = f"{base_slug}-{secrets.token_hex(4)}"
            
            if file and file.filename != '' and allowed_file(file.filename):
                new_image_url = upload_to_cloudinary(file, 'posts', width=1080)
                if new_image_url:
                    delete_from_cloudinary(post.cover_image)
                    post.cover_image = new_image_url
                
            db.session.commit()
            notify_mentions(raw_text, post.id, current_user.id)
            flash("Post updated!", category='success')
            return redirect(url_for('views.home'))

    content_to_edit = post.text
    if '\n' in content_to_edit and '<p>' not in content_to_edit and '<br>' not in content_to_edit:
        content_to_edit = content_to_edit.replace('\n', '<br>')

    return render_template("edit_post.html", user=current_user, post=post, content_to_edit=content_to_edit)

# 🚀 NEW: Route now accepts a string (slug) instead of just an int
@views.route("/post/<string:slug>")
def post_view(slug):
    # Try to fetch by the new SEO slug first
    post = Post.query.options(
        joinedload(Post.user),
        subqueryload(Post.likes),
        subqueryload(Post.comments).joinedload(Comment.user)
    ).filter_by(slug=slug).first()
    
    # Fallback for older posts created before slugs were added
    if not post and slug.isdigit():
        post = Post.query.options(
            joinedload(Post.user),
            subqueryload(Post.likes),
            subqueryload(Post.comments).joinedload(Comment.user)
        ).get_or_404(int(slug))
    elif not post:
        abort(404)
        
    if current_user.is_authenticated:
        blockers, blocked_by_me = get_block_lists(current_user.id) 
        all_blocked_ids = list(set(blockers + blocked_by_me))
    else:
        all_blocked_ids = []
    
    if post.author in all_blocked_ids:
        flash("You cannot view this post.", category='error')
        return redirect(url_for('views.home'))
        
    posts = enrich_posts([post], all_blocked_ids)
    
    return render_template(
        "posts.html", 
        user=current_user, 
        posts=posts, 
        username=post.user.username,
        pagination=None 
    )

@views.route("/posts/<string:username>")
@login_required
def posts(username):
    user = User.query.filter_by(username=username).first_or_404()
    blockers, blocked_by_me = get_block_lists(current_user.id)
    all_blocked_ids = list(set(blockers + blocked_by_me)) 
    
    if user.id in all_blocked_ids:
        flash("You cannot view this user's posts.", category='error')
        return redirect(url_for('views.home'))

    page = request.args.get('page', 1, type=int)
    
    pagination = Post.query.options(
        joinedload(Post.user),
        subqueryload(Post.likes),
        subqueryload(Post.comments).joinedload(Comment.user)
    ).filter_by(author=user.id, is_deleted=False)\
    .order_by(Post.date_created.desc())\
    .paginate(page=page, per_page=10, error_out=False)
        
    posts = enrich_posts(pagination.items, all_blocked_ids)
    
    return render_template(
        "posts.html",
        user=current_user,
        posts=posts,
        pagination=pagination,
        username=user.username
    )

@views.route("/delete-post/<int:id>")
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)
    
    if current_user.id != post.author and not current_user.is_admin:
        flash("You do not have permission to delete this post.", category='error')
    else:
        post.is_deleted = True
        db.session.commit()
        flash('Post moved to trash.', category='success')

    return redirect(request.referrer or url_for('views.home'))

# =================================================
# COMMENTS, LIKES & SAVES
# =================================================

@views.route("/create-comment/<int:post_id>", methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def create_comment(post_id):
    text = request.form.get('text')

    if not text:
        flash('Invalid submission.', category='error')
    else:
        post = Post.query.filter_by(id=post_id).first()
        if post:
            clean_text = bleach.clean(text, tags=[], strip=True)
            final_text = process_text_links(clean_text)
            
            comment = Comment(
                text=final_text, 
                author=current_user.id, 
                post_id=post_id,
                date_created=datetime.now(timezone.utc).replace(tzinfo=None) 
            )
            
            db.session.add(comment)
            db.session.commit()
            
            create_notification(current_user.id, post.author, 'comment', post.id)
            notify_mentions(text, post.id, current_user.id) 
            
            flash('Comment added!', category='success')
        else:
            flash('Post does not exist.', category='error')

    return redirect(url_for('views.home'))

@views.route("/delete-comment/<int:comment_id>")
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if current_user.id != comment.author and not current_user.is_admin:
        flash('You do not have permission to delete this comment.', category='error')
    else:
        comment.is_deleted = True
        db.session.commit()
        flash('Comment deleted.', category='success')

    return redirect(request.referrer or url_for('views.home'))

@views.route("/like-post/<int:post_id>", methods=['POST'])
@login_required
@limiter.limit("60 per minute") 
def like(post_id):
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(author=current_user.id, post_id=post_id).first()

    liked = False
    if like:
        db.session.delete(like)
        db.session.commit()
    else:
        like = Like(author=current_user.id, post_id=post_id, date_created=datetime.now(timezone.utc).replace(tzinfo=None)) 
        db.session.add(like)
        db.session.commit()
        liked = True
        create_notification(current_user.id, post.author, 'like', post.id)

    return jsonify({"likes": len(post.likes), "liked": liked})

@views.route("/save-post/<int:post_id>", methods=['POST'])
@login_required
@limiter.limit("60 per minute")
def save_post(post_id):
    post = Post.query.get_or_404(post_id)
    saved_post = SavedPost.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    saved = False

    if saved_post:
        db.session.delete(saved_post)
        db.session.commit()
    else:
        new_save = SavedPost(user_id=current_user.id, post_id=post_id, date_created=datetime.now(timezone.utc).replace(tzinfo=None)) 
        db.session.add(new_save)
        db.session.commit()
        saved = True

    saves_count = len(post.saved_by)
    return jsonify({"saved": saved, "saves_count": saves_count})

# =================================================
# NOTIFICATIONS SYSTEM
# =================================================

@views.route('/notifications')
@login_required
def notifications():
    unread_notifs = Notification.query.options(joinedload(Notification.visitor))\
        .filter_by(recipient_id=current_user.id, is_read=False)\
        .order_by(Notification.date_created.desc()).limit(30).all()
        
    read_notifs = Notification.query.options(joinedload(Notification.visitor))\
        .filter_by(recipient_id=current_user.id, is_read=True)\
        .order_by(Notification.date_created.desc()).limit(100).all()
        
    def process_groups(notifs):
        grouped = []
        seen = {}
        
        for n in notifs:
            if n.post_id and n.action in ['like', 'comment', 'mention']:
                key = (n.action, n.post_id)
                if key not in seen:
                    n.is_grouped = False
                    n.others_count = 0
                    seen[key] = n
                    grouped.append(n)
                else:
                    seen[key].is_grouped = True
                    seen[key].others_count += 1
            else:
                n.is_grouped = False
                grouped.append(n)
        
        for n in grouped:
            if getattr(n, 'is_grouped', False):
                c = n.others_count
                if c >= 1000:
                    n.others_text = "1k+"
                elif c >= 50:
                    n.others_text = "50+"
                elif c >= 10:
                    n.others_text = "10+"
                elif c >= 5:
                    n.others_text = "5+"
                else:
                    n.others_text = str(c)
        return grouped

    grouped_unread = process_groups(unread_notifs)
    grouped_read = process_groups(read_notifs)[:5] 
    
    final_notifs = grouped_unread + grouped_read
    final_notifs.sort(key=lambda x: x.date_created, reverse=True)

    if unread_notifs:
        for notif in unread_notifs:
            notif.is_read = True
        db.session.commit()

    return render_template("notifications.html", user=current_user, notifications=final_notifs)

@views.route('/api/mark-notifications-read', methods=['POST'])
@login_required
def mark_notifications_read():
    unread_notifs = Notification.query.filter_by(recipient_id=current_user.id, is_read=False).all()
    for n in unread_notifs:
        n.is_read = True
    db.session.commit()
    return jsonify({'success': True})

# =================================================
# PROFILE & SETTINGS
# =================================================

@views.route("/profile/<string:username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    blockers, blocked_by_me = get_block_lists(current_user.id)
    all_blocked_ids = list(set(blockers + blocked_by_me))

    if user.id in blockers:
        flash("You cannot view this profile.", category='error')
        return redirect(url_for('views.home'))
        
    i_have_blocked_them = user.id in blocked_by_me

    if user.is_admin and not current_user.is_admin:
        flash('This profile is private and cannot be viewed.', category='error')
        return redirect(url_for('views.home'))

    page = request.args.get('page', 1, type=int)
    tab = request.args.get('tab', 'posts') 

    if tab == 'saved' and current_user.id == user.id:
        pagination = Post.query.join(SavedPost, SavedPost.post_id == Post.id)\
            .options(
                joinedload(Post.user),
                subqueryload(Post.likes),
                subqueryload(Post.comments).joinedload(Comment.user)
            ).filter(SavedPost.user_id == user.id, Post.is_deleted == False, ~Post.author.in_(all_blocked_ids))\
            .order_by(SavedPost.date_created.desc())\
            .paginate(page=page, per_page=5, error_out=False)
    else:
        tab = 'posts' 
        pagination = Post.query.options(
            joinedload(Post.user),
            subqueryload(Post.likes),
            subqueryload(Post.comments).joinedload(Comment.user)
        ).filter_by(author=user.id, is_deleted=False)\
        .order_by(Post.date_created.desc())\
        .paginate(page=page, per_page=5, error_out=False)

    posts = enrich_posts(pagination.items, all_blocked_ids)
    
    followers_count = Follow.query.filter_by(following_id=user.id).count()
    following_count = Follow.query.filter_by(follower_id=user.id).count()
    total_posts = Post.query.filter_by(author=user.id, is_deleted=False).count()
    
    is_following = Follow.query.filter_by(
        follower_id=current_user.id, 
        following_id=user.id
    ).first()

    return render_template(
        "profile.html", 
        user=current_user, 
        profile_user=user, 
        posts=posts, 
        pagination=pagination, 
        followers_count=followers_count,
        following_count=following_count,
        total_posts=total_posts,
        is_following=is_following,
        tab=tab,
        i_have_blocked_them=i_have_blocked_them 
    )
    
@views.route('/update-profile-pic', methods=['POST'])
@login_required
@limiter.limit("10 per hour") 
def update_profile_pic():
    if 'profile_pic' not in request.files:
        flash('No file provided.', category='error')
        return redirect(url_for('views.profile', username=current_user.username))
    
    file = request.files['profile_pic']
    if file.filename == '':
        flash('No selected file.', category='error')
        return redirect(url_for('views.profile', username=current_user.username))
        
    if file and allowed_file(file.filename):
        image_url = upload_to_cloudinary(file, 'avatars', width=300, height=300)
        if image_url:
            delete_from_cloudinary(current_user.profile_pic)
            
            current_user.profile_pic = image_url
            db.session.commit()
            flash('Profile picture updated!', category='success')
        else:
            flash('Error uploading to cloud storage.', category='error')
    else:
        flash('Invalid file type. Please upload JPG, PNG, or WEBP image.', category='error')
        
    return redirect(url_for('views.profile', username=current_user.username))

@views.route('/edit-bio', methods=['POST'])
@login_required
@limiter.limit("20 per hour") 
def edit_bio():
    new_bio = request.form.get('bio')
    if len(new_bio) > 300:
        flash('Bio is too long (max 300 chars).', category='error')
    else:
        current_user.bio = new_bio
        db.session.commit()
        flash('Bio updated!', category='success')
    return redirect(url_for('views.profile', username=current_user.username))

RESERVED_USERNAMES = {
    'avpostory','av_postory','home', 'login', 'logout', 'sign-up', 'signup', 'register',
    'inbox', 'chat', 'messages', 'notifications', 'search', 'explore',
    'admin', 'dashboard', 'settings', 'profile', 'user', 'users',
    'static', 'assets', 'uploads', 'images', 'css', 'js',
    'api', 'about', 'contact', 'help', 'support', 'terms', 'privacy',
    'create-post', 'edit-post', 'delete', 'update', 'deactivate'
}

@views.route('/check-username', methods=['POST'])
@limiter.limit("30 per minute") 
def check_username():
    data = request.get_json()
    username = data.get('username')
    
    if not username:
        return jsonify({'available': False, 'message': 'Please enter a username'})
    
    username = username.strip()
    
    if len(username) < 3:
         return jsonify({'available': False, 'message': 'Too short (min 3 chars)'})

    if not re.match("^[a-zA-Z0-9_.]+$", username):
         return jsonify({'available': False, 'message': 'Invalid characters. Use letters, numbers, . and _'})

    if username.lower() in RESERVED_USERNAMES:
        return jsonify({'available': False, 'message': 'This username is reserved by the system.'})

    user = User.query.filter_by(username=username).first()
    
    if user:
        if current_user.is_authenticated and user.id == current_user.id:
             return jsonify({'available': False, 'message': 'This username is already owned by you.'})
        return jsonify({'available': False, 'message': 'This username already exists.'})
    
    return jsonify({'available': True, 'message': 'This username is unique and you can take it.'})

@views.route('/change-username', methods=['POST'])
@login_required
@limiter.limit("5 per day") 
def change_username():
    new_username = request.form.get('username')
    
    if not new_username:
        flash("Username cannot be empty.", category='error')
        return redirect(url_for('views.profile', username=current_user.username))

    new_username = new_username.strip()

    if len(new_username) < 3:
        flash("Username must be at least 3 characters.", category='error')
    
    elif not re.match("^[a-zA-Z0-9_.]+$", new_username):
        flash("Invalid format! Use letters, numbers, dots (.), and underscores (_).", category='error')
    
    elif new_username.lower() in RESERVED_USERNAMES:
        flash("This username is reserved by the system.", category='error')

    else:
        existing = User.query.filter_by(username=new_username).first()
        if existing:
            flash("Username already taken.", category='error')
        else:
            current_user.username = new_username
            db.session.commit()
            flash("Username updated! Please login again.", category='success')
            return redirect(url_for('auth.logout'))
            
    return redirect(url_for('views.profile', username=current_user.username))

@views.route('/add-social-link', methods=['POST'])
@login_required
@limiter.limit("20 per hour") 
def add_social_link():
    link = request.form.get('new_link')
    if not link:
        flash("Link cannot be empty", category='error')
    else:
        platform = detect_platform(link)
        current_links = dict(current_user.social_links) if current_user.social_links else {}
        key = platform
        counter = 1
        while key in current_links:
            key = f"{platform}_{counter}"
            counter += 1
        current_links[key] = link
        current_user.social_links = current_links
        flag_modified(current_user, "social_links")
        db.session.commit()
        flash("Link added!", category='success')
    return redirect(url_for('views.profile', username=current_user.username))

# =================================================
# SAFETY & MODERATION ROUTES 
# =================================================

@views.route('/block/<int:user_id>', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def block_user(user_id):
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot block yourself'})
    
    existing = Block.query.filter_by(blocker_id=current_user.id, blocked_id=user_id).first()
    if not existing:
        new_block = Block(blocker_id=current_user.id, blocked_id=user_id, date_created=datetime.now(timezone.utc).replace(tzinfo=None))
        db.session.add(new_block)
        
        Follow.query.filter(or_(
            and_(Follow.follower_id == current_user.id, Follow.following_id == user_id),
            and_(Follow.follower_id == user_id, Follow.following_id == current_user.id)
        )).delete()
        
        db.session.commit()
        return jsonify({'success': True, 'action': 'blocked'})
    return jsonify({'success': False, 'message': 'Already blocked'})

@views.route('/unblock/<int:user_id>', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def unblock_user(user_id):
    block_record = Block.query.filter_by(blocker_id=current_user.id, blocked_id=user_id).first()
    if block_record:
        db.session.delete(block_record)
        db.session.commit()
        return jsonify({'success': True, 'action': 'unblocked'})
    return jsonify({'success': False, 'message': 'Not blocked'})

@views.route('/report/<string:item_type>/<int:item_id>', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def report_item(item_type, item_id):
    data = request.get_json()
    reason = data.get('reason', 'Inappropriate content')
    
    if item_type == 'post':
        existing = Report.query.filter_by(reporter_id=current_user.id, post_id=item_id).first()
        if not existing:
            new_report = Report(reporter_id=current_user.id, post_id=item_id, reason=reason)
            db.session.add(new_report)
    elif item_type == 'comment':
        existing = Report.query.filter_by(reporter_id=current_user.id, comment_id=item_id).first()
        if not existing:
            new_report = Report(reporter_id=current_user.id, comment_id=item_id, reason=reason)
            db.session.add(new_report)
            
    db.session.commit()
    return jsonify({'success': True, 'message': 'Report submitted for review.'})


# =================================================
# ADMIN ROUTES
# =================================================

@views.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)
        
    users = User.query.all()
    
    active_posts = Post.query.filter(
        or_(Post.is_deleted == False, Post.is_deleted == None)
    ).all()
    
    deleted_posts = Post.query.filter_by(is_deleted=True).all()
    comments = Comment.query.order_by(Comment.date_created.desc()).limit(50).all()
    reports = Report.query.filter_by(is_resolved=False).order_by(Report.date_created.desc()).all()

    raw_blocks = Block.query.order_by(Block.date_created.desc()).all()
    blocks_data = []
    for b in raw_blocks:
        blocker = User.query.get(b.blocker_id)
        blocked = User.query.get(b.blocked_id)
        if blocker and blocked:
            blocks_data.append({
                'id': b.id,
                'blocker': blocker,
                'blocked': blocked,
                'date_created': b.date_created
            })

    return render_template(
        "admin_dashboard.html",
        users=users,
        active_posts=active_posts,
        deleted_posts=deleted_posts,
        comments=comments,
        reports=reports, 
        blocks_data=blocks_data, 
        user=current_user
    )

@views.route('/admin/remove-block/<int:block_id>', methods=['POST'])
@login_required
def admin_remove_block(block_id):
    if not current_user.is_admin: abort(403)
    
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    block_record = Block.query.get_or_404(block_id)
    db.session.delete(block_record)
    db.session.commit()
    flash("Block successfully removed by Admin.", category='success')
    return redirect(url_for('views.admin_dashboard'))


@views.route('/admin/resolve-report/<int:report_id>', methods=['POST'])
@login_required
def admin_resolve_report(report_id):
    if not current_user.is_admin:
        abort(403)
        
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    report = Report.query.get_or_404(report_id)
    report.is_resolved = True
    
    action = request.form.get('action')
    if action == 'delete_content':
        if report.post_id:
            p = Post.query.get(report.post_id)
            if p: p.is_deleted = True
        elif report.comment_id:
            c = Comment.query.get(report.comment_id)
            if c: c.is_deleted = True
            
    db.session.commit()
    flash('Report marked as resolved.', category='success')
    return redirect(url_for('views.admin_dashboard'))

@views.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        abort(403)
    
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.is_admin:
         flash("Cannot delete another admin", category='error')
    else:
        delete_from_cloudinary(user_to_delete.profile_pic)
        delete_from_cloudinary(user_to_delete.cover_pic)
        
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f"User {user_to_delete.username} deleted permanently.", category='success')
        
    return redirect(url_for('views.admin_dashboard'))

@views.route("/restore-post/<int:id>")
@login_required
def restore_post(id):
    post = Post.query.get_or_404(id)
    
    if not current_user.is_admin:
        flash("Only Admins can restore posts.", category='error')
    else:
        post.is_deleted = False
        db.session.commit()
        flash('Post restored successfully!', category='success')

    return redirect(request.referrer or url_for('views.admin_dashboard'))

@views.route('/admin/toggle-user-status/<int:user_id>', methods=['POST'])
@login_required
def admin_toggle_user_status(user_id):
    if not current_user.is_admin:
        abort(403)
        
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))

    user = User.query.get_or_404(user_id)
    
    if user.is_admin:
        flash('Cannot deactivate an admin.', category='error')
        return redirect(url_for('views.admin_dashboard'))

    user.is_active = not user.is_active
    db.session.commit()
    
    status = "Active" if user.is_active else "Deactivated"
    flash(f"User {user.username} is now {status}.", category='success')
    return redirect(url_for('views.admin_dashboard'))

@views.route('/admin/delete-post/<int:post_id>', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    if not current_user.is_admin:
        abort(403)
        
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    post = Post.query.get_or_404(post_id)
    post.is_deleted = True
    db.session.commit()
    flash("Post moved to trash.", category='success')
    return redirect(url_for('views.admin_dashboard'))

@views.route('/admin/permanent-delete-post/<int:post_id>', methods=['POST'])
@login_required
def admin_permanent_delete_post(post_id):
    if not current_user.is_admin:
        abort(403)
        
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    post = Post.query.get_or_404(post_id)
    delete_from_cloudinary(post.cover_image)
    db.session.delete(post)
    db.session.commit()
    flash("Post permanently deleted.", category='success')
    return redirect(url_for('views.admin_dashboard'))

@views.route('/admin/delete-comment/<int:comment_id>', methods=['POST'])
@login_required
def admin_delete_comment(comment_id):
    if not current_user.is_admin:
        abort(403)
        
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    comment = Comment.query.get_or_404(comment_id)
    comment.is_deleted = True
    db.session.commit()
    flash("Comment hidden.", category='success')
    return redirect(url_for('views.admin_dashboard'))

@views.route('/admin-permanent-delete-comment/<int:comment_id>', methods=['POST'])
@login_required
def admin_permanent_delete_comment(comment_id):
    if not current_user.is_admin:
        flash("Access denied.", category='error')
        return redirect(url_for('views.home'))

    admin_password = request.form.get('admin_password')
    if not check_password_hash(current_user.password, admin_password):
        flash("Invalid admin password.", category='error')
        return redirect(url_for('views.admin_dashboard'))

    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    flash('Comment permanently deleted.', category='success')
        
    return redirect(url_for('views.admin_dashboard'))

@views.route('/admin/restore-comment/<int:comment_id>', methods=['POST'])
@login_required
def admin_restore_comment(comment_id):
    if not current_user.is_admin:
        abort(403)
        
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    comment = Comment.query.get_or_404(comment_id)
    comment.is_deleted = False
    db.session.commit()
    flash("Comment restored.", category='success')
    return redirect(url_for('views.admin_dashboard'))

@views.route('/admin/restore-post/<int:post_id>', methods=['POST'])
@login_required
def admin_restore_post(post_id):
    if not current_user.is_admin: abort(403)
    
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    post = Post.query.get_or_404(post_id)
    post.is_deleted = False
    db.session.commit()
    flash("Post restored.", category='success')
    return redirect(url_for('views.admin_dashboard'))

# =================================================
# SEARCH & FOLLOW
# =================================================

@views.route('/follow/<int:user_id>', methods=['POST'])
@login_required
@limiter.limit("60 per minute") 
def follow_user(user_id):
    user_to_follow = User.query.get_or_404(user_id)
    if user_to_follow.id == current_user.id:
        return jsonify({'error': 'Cannot follow self'}), 400
        
    blockers, blocked_by_me = get_block_lists(current_user.id)
    all_blocked_ids = list(set(blockers + blocked_by_me)) 
    
    if user_id in all_blocked_ids:
        return jsonify({'success': False, 'message': 'Cannot follow this user'})
        
    existing = Follow.query.filter_by(follower_id=current_user.id, following_id=user_id).first()
    if not existing:
        new_follow = Follow(follower_id=current_user.id, following_id=user_id, date_created=datetime.now(timezone.utc).replace(tzinfo=None)) 
        db.session.add(new_follow)
        db.session.commit()
        create_notification(current_user.id, user_id, 'follow')
        
        return jsonify({'success': True, 'action': 'followed'})
        
    return jsonify({'success': False, 'message': 'Already following'})

@views.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
@limiter.limit("60 per minute") 
def unfollow_user(user_id):
    follow_record = Follow.query.filter_by(follower_id=current_user.id, following_id=user_id).first()
    if follow_record:
        db.session.delete(follow_record)
        db.session.commit()
        return jsonify({'success': True, 'action': 'unfollowed'})
    return jsonify({'success': False, 'message': 'Not following'})

@views.route("/followers/<string:username>")
@login_required
def followers_list(username):
    user = User.query.filter_by(username=username).first_or_404()
    blockers, blocked_by_me = get_block_lists(current_user.id)
    all_blocked_ids = list(set(blockers + blocked_by_me)) 
    
    if user.id in all_blocked_ids:
        flash("You cannot view this information.", category='error')
        return redirect(url_for('views.home'))
        
    followers = User.query.join(Follow, Follow.follower_id == User.id)\
        .filter(Follow.following_id == user.id, ~User.id.in_(all_blocked_ids)).all()
    following_ids = {f.following_id for f in Follow.query.filter_by(follower_id=current_user.id).all()}
    return render_template("followers.html", profile_user=user, users=followers, following_ids=following_ids, title="Followers")

@views.route("/following/<string:username>")
@login_required
def following_list(username):
    user = User.query.filter_by(username=username).first_or_404()
    blockers, blocked_by_me = get_block_lists(current_user.id)
    all_blocked_ids = list(set(blockers + blocked_by_me)) 
    
    if user.id in all_blocked_ids:
        flash("You cannot view this information.", category='error')
        return redirect(url_for('views.home'))
        
    following = User.query.join(Follow, Follow.following_id == User.id)\
        .filter(Follow.follower_id == user.id, ~User.id.in_(all_blocked_ids)).all()
    following_ids = {f.following_id for f in Follow.query.filter_by(follower_id=current_user.id).all()}
    return render_template("followers.html", profile_user=user, users=following, following_ids=following_ids, title="Following")

# =================================================
# ACCOUNT DEACTIVATION
# =================================================

@views.route('/deactivate-account', methods=['POST'])
@login_required
def deactivate_account():
    if current_user.is_admin:
        flash("Admin accounts cannot be deactivated. You are the boss!", category='error')
        return redirect(url_for('views.profile', username=current_user.username))

    reason = request.form.get('reason')
    details = request.form.get('details')
    full_reason = f"Reason: {reason} | Details: {details}" if details else reason
    
    current_user.deactivation_reason = full_reason
    current_user.is_active = False
    
    db.session.commit()
    logout_user() 
    
    flash('Your account has been deactivated. We hope to see you again!', category='success')
    return redirect(url_for('auth.login'))

# =================================================
# API ROUTES (SEARCH)
# =================================================



@views.route('/api/search-users', methods=['GET'])
@limiter.limit("60 per minute") 
def search_users_api():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
        
    blockers, _ = get_block_lists(current_user.id) if current_user.is_authenticated else ([], [])

    users = User.query.filter(
        User.username.ilike(f'%{q}%'),
        User.is_admin == False,
        ~User.id.in_(blockers)
    ).limit(5).all()

    results = []
    for u in users:
        results.append({
            'username': u.username,
            'profile_pic': u.profile_pic,
        })
    return jsonify(results)

@views.route("/search-page")
@login_required
def search_page():
    query = request.args.get('q', '').strip()
    blockers, blocked_by_me = get_block_lists(current_user.id)
    all_blocked_ids = list(set(blockers + blocked_by_me))
    
    users = []
    posts = []
    
    if query:
        users = User.query.filter(
            User.username.ilike(f"%{query}%"),
            User.is_admin == False,
            ~User.id.in_(blockers) 
        ).all()
        
        posts = Post.query.filter(
            Post.text.ilike(f"%{query}%"),
            Post.is_deleted == False,
            ~Post.author.in_(all_blocked_ids)
        ).options(
            joinedload(Post.user),
            subqueryload(Post.likes),
            subqueryload(Post.comments).joinedload(Comment.user)
        ).order_by(Post.date_created.desc()).all()

        words = query.split()
        if not users and not posts and len(words) > 1:
            user_conditions = [User.username.ilike(f"%{word}%") for word in words]
            post_conditions = [Post.text.ilike(f"%{word}%") for word in words]
            
            users = User.query.filter(
                or_(*user_conditions),
                User.is_admin == False,
                ~User.id.in_(blockers)
            ).all()
            
            posts = Post.query.filter(
                or_(*post_conditions),
                Post.is_deleted == False,
                ~Post.author.in_(all_blocked_ids)
            ).options(
                joinedload(Post.user),
                subqueryload(Post.likes),
                subqueryload(Post.comments).joinedload(Comment.user)
            ).order_by(Post.date_created.desc()).all()

        if len(users) < 5 or len(posts) < 5:
            found_user_ids = [u.id for u in users]
            found_user_ids.append(current_user.id) 
            found_user_ids.extend(blockers) 
            
            found_post_ids = [p.id for p in posts]
            added_recommendations = False
            
            if len(users) < 5:
                extra_users = User.query.filter(
                    User.is_admin == False,
                    ~User.id.in_(found_user_ids) 
                ).order_by(func.random()).limit(5).all()
                
                if extra_users:
                    users.extend(extra_users)
                    added_recommendations = True
                    
            if len(posts) < 5:
                extra_posts = Post.query.filter(
                    Post.is_deleted == False,
                    ~Post.id.in_(found_post_ids),
                    ~Post.author.in_(all_blocked_ids)
                ).options(
                    joinedload(Post.user),
                    subqueryload(Post.likes),
                    subqueryload(Post.comments).joinedload(Comment.user)
                ).order_by(func.random()).limit(10).all()
                
                if extra_posts:
                    posts.extend(extra_posts)
                    added_recommendations = True
            
            if added_recommendations:
                flash(f"Showing results for '{query}' along with some recommended content!", category='info')

    else:
        users = User.query.filter(
            User.is_admin == False,
            User.id != current_user.id,
            ~User.id.in_(blockers)
        ).order_by(func.random()).limit(5).all()
        
        posts = Post.query.filter_by(is_deleted=False)\
            .filter(~Post.author.in_(all_blocked_ids))\
            .options(
                joinedload(Post.user),
                subqueryload(Post.likes),
                subqueryload(Post.comments).joinedload(Comment.user)
            ).order_by(func.random()).limit(10).all()
    
    if posts:
        posts = enrich_posts(posts, all_blocked_ids)

    return render_template("search.html", user=current_user, users=users, posts=posts, query=query)

@views.route('/profile/remove-social', methods=['POST'])
@login_required
def remove_social():
    data = request.get_json()
    url_to_remove = data.get('url')
    
    if not url_to_remove:
        return jsonify({'success': False, 'message': 'No URL provided'})
    
    links = dict(current_user.social_links) if current_user.social_links else {}
    
    key_to_delete = None
    for key, value in links.items():
        if value == url_to_remove:
            key_to_delete = key
            break
            
    if key_to_delete:
        del links[key_to_delete]
        current_user.social_links = links
        flag_modified(current_user, "social_links")
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Link not found'})

@views.route('/update-cover-pic', methods=['POST'])
@login_required
@limiter.limit("10 per hour") 
def update_cover_pic():
    if 'cover_pic' not in request.files:
        flash('No file provided.', category='error')
        return redirect(url_for('views.profile', username=current_user.username))
    
    file = request.files['cover_pic']
    
    if file.filename == '':
        flash('No selected file.', category='error')
        return redirect(url_for('views.profile', username=current_user.username))
        
    if file and allowed_file(file.filename):
        image_url = upload_to_cloudinary(file, 'posts', width=1080, height=600)
        if image_url:
            delete_from_cloudinary(current_user.cover_pic)
            
            current_user.cover_pic = image_url
            db.session.commit()
            flash('Cover photo updated!', category='success')
        else:
            flash('Error uploading to cloud storage.', category='error')
    else:
        flash('Invalid file type.', category='error')
        
    return redirect(url_for('views.profile', username=current_user.username))

@views.route("/like-comment/<int:comment_id>", methods=['POST'])
@login_required
@limiter.limit("60 per minute") 
def like_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    like = CommentLike.query.filter_by(author=current_user.id, comment_id=comment_id).first()
    liked = False

    if like:
        db.session.delete(like)
        liked = False
    else:
        like = CommentLike(author=current_user.id, comment_id=comment_id, date_created=datetime.now(timezone.utc).replace(tzinfo=None)) 
        db.session.add(like)
        liked = True

    db.session.commit()
    return jsonify({"likes": len(comment.likes), "liked": liked})


    
# =================================================
# MESSAGING SYSTEM (Inbox & Chat)
# =================================================

@views.route('/inbox')
@login_required
def inbox():
    blockers, blocked_by_me = get_block_lists(current_user.id)
    all_blocked_ids = list(set(blockers + blocked_by_me))
    
    messages = Message.query.options(
        joinedload(Message.sender), 
        joinedload(Message.recipient)
    ).filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.visible_to_sender == True),
            and_(Message.recipient_id == current_user.id, Message.visible_to_recipient == True)
        )
    ).order_by(Message.date_created.desc()).all()
    
    conversations = {}
    for msg in messages:
        partner = msg.recipient if msg.sender_id == current_user.id else msg.sender
        
        if partner.id in all_blocked_ids:
            continue
            
        if partner.id not in conversations:
            conversations[partner.id] = {
                'user': partner,
                'last_message': msg,
                'unread': (not msg.is_read and msg.recipient_id == current_user.id)
            }
    
    return render_template("inbox.html", user=current_user, chats=list(conversations.values()))

@views.route('/chat/<string:username>')
@login_required
def chat(username):
    recipient = User.query.filter_by(username=username).first_or_404()
    
    blockers, blocked_by_me = get_block_lists(current_user.id)
    all_blocked_ids = list(set(blockers + blocked_by_me))
    
    if recipient.id in all_blocked_ids:
        flash("You cannot message this user.", category='error')
        return redirect(url_for('views.inbox'))

    unread_msgs = Message.query.filter_by(
        sender_id=recipient.id, 
        recipient_id=current_user.id, 
        is_read=False
    ).all()

    if unread_msgs:
        for msg in unread_msgs:
            msg.is_read = True
        db.session.commit()

    messages_desc = Message.query.filter(
        or_(
            and_(
                Message.sender_id == current_user.id,
                Message.recipient_id == recipient.id,
                Message.visible_to_sender == True 
            ),
            and_(
                Message.sender_id == recipient.id,
                Message.recipient_id == current_user.id,
                Message.visible_to_recipient == True 
            )
        )
    ).order_by(Message.date_created.desc()).limit(50).all() 
    
    messages = list(reversed(messages_desc))

    return render_template("chat.html", user=current_user, recipient=recipient, messages=messages)

@views.route('/api/chat-history/<int:recipient_id>')
@login_required
@limiter.limit("60 per minute") 
def chat_history(recipient_id):
    offset = request.args.get('offset', 50, type=int)
    
    older_messages_desc = Message.query.filter(
        or_(
            and_(
                Message.sender_id == current_user.id, 
                Message.recipient_id == recipient_id,
                Message.visible_to_sender == True
            ),
            and_(
                Message.sender_id == recipient_id, 
                Message.recipient_id == current_user.id,
                Message.visible_to_recipient == True
            )
        )
    ).order_by(Message.date_created.desc()).offset(offset).limit(50).all()

    data = []
    for msg in older_messages_desc:
        data.append({
            'id': msg.id, 
            'text': msg.text,
            'sender_id': msg.sender_id,
            'time': msg.date_created.isoformat() + 'Z' 
        })
    
    return jsonify(data)

@views.route('/api/delete-message/<int:id>', methods=['POST'])
@login_required
def delete_message(id):
    msg = Message.query.get_or_404(id)

    if msg.sender_id == current_user.id:
        msg.visible_to_sender = False 
    elif msg.recipient_id == current_user.id:
        msg.visible_to_recipient = False 
    else:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.commit()
    return jsonify({'success': True})

@views.route('/api/clear-chat/<int:recipient_id>', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def clear_chat(recipient_id):
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.recipient_id == recipient_id),
            and_(Message.sender_id == recipient_id, Message.recipient_id == current_user.id)
        )
    ).all()
    
    for msg in messages:
        if msg.sender_id == current_user.id:
            msg.visible_to_sender = False
        if msg.recipient_id == current_user.id:
            msg.visible_to_recipient = False
            
    db.session.commit()
    return jsonify({'success': True})

@views.route('/api/get-messages/<int:recipient_id>')
@login_required
def get_new_messages(recipient_id):
    last_id = request.args.get('last_id', 0, type=int) 

    new_messages = Message.query.filter(
        or_(
            and_(
                Message.sender_id == current_user.id, 
                Message.recipient_id == recipient_id,
                Message.visible_to_sender == True
            ),
            and_(
                Message.sender_id == recipient_id, 
                Message.recipient_id == current_user.id,
                Message.visible_to_recipient == True
            )
        )
    ).filter(Message.id > last_id).order_by(Message.date_created.asc()).all()

    data = []
    for msg in new_messages:
        data.append({
            'id': msg.id,
            'text': msg.text,
            'sender_id': msg.sender_id,
            'time': msg.date_created.isoformat() + 'Z' 
        })
    
    return jsonify(data)

@views.route('/api/send-message', methods=['POST'])
@login_required
@limiter.limit("60 per minute") 
def send_message():
    data = request.json
    recipient_id = data.get('recipient')
    raw_text = data.get('text')
    
    if not raw_text or not recipient_id:
        return jsonify({'success': False}), 400
        
    blockers, blocked_by_me = get_block_lists(current_user.id)
    if recipient_id in blocked_by_me or recipient_id in blockers:
        return jsonify({'success': False, 'message': 'Cannot send message.'}), 403
        
    clean_text = bleach.clean(raw_text, tags=[], strip=True)
    final_text = process_text_links(clean_text)
    
    new_message = Message(
        text=final_text, 
        sender_id=current_user.id, 
        recipient_id=recipient_id,
        date_created=datetime.now(timezone.utc).replace(tzinfo=None) 
    )
    db.session.add(new_message)
    db.session.commit()
    
    create_notification(current_user.id, recipient_id, 'message')
    
    return jsonify({
        'success': True, 
        'id': new_message.id,
        'text': new_message.text, 
        'time': new_message.date_created.isoformat() + 'Z' 
    })

# =================================================
# SEO & CRAWLER ROUTES (robots.txt & sitemap.xml)
# =================================================

@views.route('/robots.txt')
def robots_txt():
    # Dynamically generate the sitemap URL based on your current domain
    sitemap_url = url_for('views.sitemap', _external=True)
    
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /api/",
        f"Sitemap: {sitemap_url}"
    ]
    resp = make_response("\n".join(lines))
    resp.headers['Content-Type'] = 'text/plain'
    return resp

@views.route('/sitemap.xml')
def sitemap():
    # Fetch the 100 most recent active posts
    posts = Post.query.filter_by(is_deleted=False).order_by(Post.date_created.desc()).limit(100).all()
    
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    # 1. Add Homepage
    home_url = url_for('views.home', _external=True)
    xml.append(f'<url><loc>{home_url}</loc></url>')
    
    # 2. Add Posts (🚀 Uses your new SEO SLUGS!)
    for post in posts:
        # Fallback to ID if a post is old and doesn't have a slug yet
        post_url = url_for('views.post_view', slug=post.slug or post.id, _external=True)
        last_mod = post.date_created.strftime("%Y-%m-%d")
        xml.append(f'<url><loc>{post_url}</loc><lastmod>{last_mod}</lastmod></url>')
        
    xml.append('</urlset>')
    
    resp = make_response('\n'.join(xml))
    resp.headers['Content-Type'] = 'application/xml'
    return resp

# =================================================
# ERROR HANDLERS
# =================================================

@views.app_errorhandler(429)
def ratelimit_handler(e):
    if request.is_json or request.path.startswith('/api/') or request.path.startswith('/like') or request.path.startswith('/save'):
        return jsonify({'error': f"Slow down! {e.description}", 'success': False}), 429
    
    flash(f"Whoa there! You are doing that too fast. {e.description}", category='error')
    return redirect(request.referrer or url_for('views.home'))

@views.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html', user=current_user), 404

@views.app_errorhandler(500)
def internal_server_error(e):
    return render_template('500.html', user=current_user), 500

@views.route('/about')
def about():
    resp = make_response(render_template("about.html", user=current_user))
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp