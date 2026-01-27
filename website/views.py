from functools import wraps
from flask import ( 
    Blueprint, render_template, request,
    flash, redirect, url_for, abort, jsonify, current_app
)
from flask_login import login_required, current_user, logout_user
from .models import User, Post, Comment, Like, Follow, Notification, CommentLike, Message
from sqlalchemy.exc import IntegrityError
from . import db
from sqlalchemy import func, or_, desc
import re, json, os
from sqlalchemy.orm.attributes import flag_modified
from PIL import Image
import secrets
from datetime import datetime

views = Blueprint('views', __name__)

# Allowed Image Extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# =================================================
# HELPER FUNCTIONS
# =================================================

def allowed_file(filename):
    """Check if the file has a valid extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compress_image(form_picture, folder, width=None, height=None):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    
    app = current_app
    upload_path = os.path.join(app.root_path, 'static/uploads', folder, picture_fn)

    if not os.path.exists(os.path.dirname(upload_path)):
        os.makedirs(os.path.dirname(upload_path))

    i = Image.open(form_picture)

    if width and height:
        i.thumbnail((width, height))
    elif width:
        w_percent = (width / float(i.size[0]))
        h_size = int((float(i.size[1]) * float(w_percent)))
        i = i.resize((width, h_size), Image.Resampling.LANCZOS)
    
    i.save(upload_path, optimize=True, quality=85)

    return picture_fn

def enrich_posts(posts):
    for post in posts:
        post.likes_count = len(post.likes)
        post.liked = False
        if current_user.is_authenticated:
            post.liked = any(l.author == current_user.id for l in post.likes)
        
        for comment in post.comments:
            comment.likes_count = len(comment.likes)
            comment.liked = False
            if current_user.is_authenticated:
                comment.liked = any(l.author == current_user.id for l in comment.likes)
    return posts

def create_notification(visitor_id, recipient_id, action, post_id=None):
    if visitor_id == recipient_id:
        return 
        
    existing = Notification.query.filter_by(
        visitor_id=visitor_id, 
        recipient_id=recipient_id, 
        action=action, 
        post_id=post_id,
        is_read=False
    ).first()
    
    if not existing:
        notif = Notification(
            visitor_id=visitor_id, 
            recipient_id=recipient_id, 
            action=action, 
            post_id=post_id,
            # ✅ FIX: Use Local Time
            date_created=datetime.now()
        )
        db.session.add(notif)
        db.session.commit()

# =================================================
# SOCIAL LINK AUTO-DETECTION
# =================================================

SOCIAL_PATTERNS = {
    "github": r"github\.com",
    "twitter": r"(twitter\.com|x\.com)",
    "linkedin": r"linkedin\.com",
    "youtube": r"(youtube\.com|youtu\.be)",
    "instagram": r"instagram\.com",
    "whatsapp": r"(wa\.me|whatsapp\.com)",
    "snapchat": r"snapchat\.com",
    "facebook": r"facebook\.com",
    "telegram": r"(t\.me|telegram\.me)",
    "website": r"^https?://"
}

def detect_platform(url: str) -> str:
    for platform, pattern in SOCIAL_PATTERNS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "link"

# =================================================
# MAIN ROUTES
# =================================================

@views.route("/", methods=['GET'])
@views.route("/home", methods=['GET'])
def home():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    pagination = Post.query.filter_by(is_deleted=False)\
        .order_by(Post.date_created.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
        
    posts = enrich_posts(pagination.items)

    if request.args.get('ajax'):
        return render_template("_posts.html", posts=posts, user=current_user)

    return render_template(
        "home.html", 
        user=current_user, 
        posts=posts, 
        pagination=pagination,
        is_home=True
    )
    
@views.route('/create-post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        text = request.form.get('text')
        cover_image_file = request.files.get('cover_image')
        cover_image_name = None

        if not text:
            flash('Post content cannot be empty!', category='error')
        else:
            if cover_image_file and cover_image_file.filename != '':
                cover_image_name = compress_image(cover_image_file, 'posts', width=1080)
            
            # ✅ FIX: Use datetime.now() (Local Time) to match your PC clock
            post = Post(
                text=text, 
                author=current_user.id, 
                cover_image=cover_image_name,
                date_created=datetime.now() 
            )
            
            db.session.add(post)
            db.session.commit()
            flash('Post created successfully!', category='success')
            return redirect(url_for('views.home'))

    return render_template('create_posts.html', user=current_user)

@views.route("/edit-post/<id>", methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)

    if current_user.id != post.author:
        flash("You cannot edit this post.", category='error')
        return redirect(url_for('views.home'))

    if request.method == "POST":
        text = request.form.get('text')
        cover_image_file = request.files.get('cover_image')
        
        if not text:
            flash("Post content cannot be empty.", category='error')
        else:
            post.text = text
            if cover_image_file and allowed_file(cover_image_file.filename):
                new_filename = compress_image(cover_image_file, 'posts', width=1080)
                post.cover_image = new_filename
                
            db.session.commit()
            flash("Post updated!", category='success')
            return redirect(url_for('views.home'))

    return render_template("edit_post.html", user=current_user, post=post)

@views.route("/posts/<username>")
@login_required
def posts(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    
    pagination = Post.query.filter_by(author=user.id, is_deleted=False)\
        .order_by(Post.date_created.desc())\
        .paginate(page=page, per_page=10, error_out=False)
        
    posts = enrich_posts(pagination.items)
    
    return render_template(
        "posts.html",
        user=current_user,
        posts=posts,
        pagination=pagination,
        username=username
    )

@views.route("/delete-post/<id>")
@login_required
def delete_post(id):
    post = Post.query.get(id)
    
    if not post:
        flash("Post does not exist.", category='error')
    elif current_user.id != post.author and not current_user.is_admin:
        flash("You do not have permission to delete this post.", category='error')
    else:
        post.is_deleted = True
        db.session.commit()
        flash('Post moved to trash.', category='success')

    return redirect(request.referrer or url_for('views.home'))

# =================================================
# COMMENTS & LIKES
# =================================================

@views.route("/create-comment/<post_id>", methods=['POST'])
@login_required
def create_comment(post_id):
    text = request.form.get('text')

    if not text:
        flash('Comment cannot be empty.', category='error')
    else:
        post = Post.query.filter_by(id=post_id).first()
        if post:
            # ✅ FIX: Use datetime.now() (Local Time)
            comment = Comment(
                text=text, 
                author=current_user.id, 
                post_id=post_id,
                date_created=datetime.now()
            )
            
            db.session.add(comment)
            db.session.commit()
            create_notification(current_user.id, post.author, 'comment', post.id)
            flash('Comment added!', category='success')
        else:
            flash('Post does not exist.', category='error')

    return redirect(url_for('views.home'))

@views.route("/delete-comment/<comment_id>")
@login_required
def delete_comment(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first()
    if not comment:
        flash('Comment does not exist.', category='error')
    elif current_user.id != comment.author and current_user.id != comment.post.author and not current_user.is_admin:
        flash('You do not have permission to delete this comment.', category='error')
    else:
        comment.is_deleted = True
        db.session.commit()
        flash('Comment deleted.', category='success')

    return redirect(request.referrer or url_for('views.home'))

@views.route("/like-post/<post_id>", methods=['POST'])
@login_required
def like(post_id):
    post = Post.query.filter_by(id=post_id).first()
    like = Like.query.filter_by(author=current_user.id, post_id=post_id).first()

    if not post:
        return jsonify({'error': 'Post not found'}), 404

    liked = False
    if like:
        db.session.delete(like)
        db.session.commit()
    else:
        # ✅ FIX: Use datetime.now() (Local Time)
        like = Like(author=current_user.id, post_id=post_id, date_created=datetime.now())
        db.session.add(like)
        db.session.commit()
        liked = True
        create_notification(current_user.id, post.author, 'like', post.id)

    return jsonify({"likes": len(post.likes), "liked": liked})

# =================================================
# NOTIFICATIONS SYSTEM
# =================================================

@views.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(recipient_id=current_user.id)\
        .order_by(Notification.date_created.desc()).limit(50).all()
    return render_template("notifications.html", user=current_user, notifications=notifs)

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

@views.route("/profile/<username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash('No user with that username exists.', category='error')
        return redirect(url_for('views.home'))

    page = request.args.get('page', 1, type=int)
    per_page = 5

    pagination = Post.query.filter_by(author=user.id, is_deleted=False)\
        .order_by(Post.date_created.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    posts = enrich_posts(pagination.items)
    
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
        is_following=is_following
    )
    
@views.route('/update-profile-pic', methods=['POST'])
@login_required
def update_profile_pic():
    if 'profile_pic' not in request.files:
        flash('No file provided.', category='error')
        return redirect(url_for('views.profile', username=current_user.username))
    
    file = request.files['profile_pic']
    if file.filename == '':
        flash('No selected file.', category='error')
        return redirect(url_for('views.profile', username=current_user.username))
        
    if file and allowed_file(file.filename):
        filename = compress_image(file, 'avatars', width=300, height=300)
        current_user.profile_pic = filename
        db.session.commit()
        flash('Profile picture updated!', category='success')
    else:
        flash('Invalid file type. Please upload a JPG, PNG, or WEBP image.', category='error')
        
    return redirect(url_for('views.profile', username=current_user.username))

@views.route('/edit-bio', methods=['POST'])
@login_required
def edit_bio():
    new_bio = request.form.get('bio')
    if len(new_bio) > 300:
        flash('Bio is too long (max 300 chars).', category='error')
    else:
        current_user.bio = new_bio
        db.session.commit()
        flash('Bio updated!', category='success')
    return redirect(url_for('views.profile', username=current_user.username))

@views.route('/check-username', methods=['POST'])
def check_username():
    data = request.get_json()
    username = data.get('username')
    
    if not username:
        return jsonify({'available': False, 'message': 'Please enter a username'})
    
    username = username.strip()
    if len(username) < 3:
         return jsonify({'available': False, 'message': 'Too short (min 3 chars)'})

    user = User.query.filter_by(username=username).first()
    
    if user:
        if current_user.is_authenticated and user.id == current_user.id:
             return jsonify({'available': False, 'message': 'This username is already owned by you.'})
        return jsonify({'available': False, 'message': 'This username already exists.'})
    
    return jsonify({'available': True, 'message': 'This username is unique and you can take it.'})

@views.route('/change-username', methods=['POST'])
@login_required
def change_username():
    new_username = request.form.get('username')
    if not new_username or len(new_username) < 3:
        flash("Username too short.", category='error')
    elif not re.match("^[a-zA-Z0-9_.]+$", new_username):
        flash("Username can only contain letters, numbers, dots, and underscores (No spaces).", category='error')
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

    return render_template(
        "admin_dashboard.html",
        users=users,
        active_posts=active_posts,
        deleted_posts=deleted_posts,
        comments=comments,
        user=current_user
    )
    
@views.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        abort(403)
    
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    user_to_delete = User.query.get(user_id)
    if user_to_delete:
        if user_to_delete.is_admin:
             flash("Cannot delete another admin", category='error')
        else:
            db.session.delete(user_to_delete)
            db.session.commit()
            flash(f"User {user_to_delete.username} deleted permanently.", category='success')
    else:
        flash("User not found", category='error')
    return redirect(url_for('views.admin_dashboard'))

@views.route("/restore-post/<id>")
@login_required
def restore_post(id):
    post = Post.query.get(id)
    
    if not post:
        flash("Post does not exist.", category='error')
    elif not current_user.is_admin:
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

    user = User.query.get(user_id)
    if not user:
        flash('User not found', category='error')
        return redirect(url_for('views.admin_dashboard'))
    
    if user.is_admin:
        flash('Cannot deactivate an admin.', category='error')
        return redirect(url_for('views.admin_dashboard'))

    user.is_active = not user.is_active
    db.session.commit()
    
    status = "Active" if user.is_active else "Deactivated"
    flash(f"User {user.username} is now {status}.", category='success')
    return redirect(url_for('views.admin_dashboard'))

# 1. UPDATE THIS: Make the standard delete 'Soft' (Move to Trash)
@views.route('/admin/delete-post/<int:post_id>', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    if not current_user.is_admin:
        abort(403)
        
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    post = Post.query.get(post_id)
    if post:
        # ✅ CHANGE: Soft Delete (Move to Trash)
        post.is_deleted = True
        db.session.commit()
        flash("Post moved to trash.", category='success')
    return redirect(url_for('views.admin_dashboard'))

# 2. ADD THIS: New route for Permanent Delete
@views.route('/admin/permanent-delete-post/<int:post_id>', methods=['POST'])
@login_required
def admin_permanent_delete_post(post_id):
    if not current_user.is_admin:
        abort(403)
        
    pwd = request.form.get('admin_password')
    if pwd != os.getenv('ADMIN_PASSWORD'):
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    post = Post.query.get(post_id)
    if post:
        # ✅ CHANGE: Hard Delete (Remove from DB)
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
        
    comment = Comment.query.get(comment_id)
    if comment:
        comment.is_deleted = True
        db.session.commit()
        flash("Comment hidden.", category='success')
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
        
    comment = Comment.query.get(comment_id)
    if comment:
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
        
    post = Post.query.get(post_id)
    if post:
        post.is_deleted = False
        db.session.commit()
        flash("Post restored.", category='success')
    return redirect(url_for('views.admin_dashboard'))

# =================================================
# SEARCH & FOLLOW
# =================================================

@views.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow_user(user_id):
    user_to_follow = User.query.get(user_id)
    if not user_to_follow:
        return jsonify({'error': 'User not found'}), 404
    if user_to_follow.id == current_user.id:
        return jsonify({'error': 'Cannot follow self'}), 400
        
    existing = Follow.query.filter_by(follower_id=current_user.id, following_id=user_id).first()
    if not existing:
        # ✅ FIX: Use Local Time
        new_follow = Follow(follower_id=current_user.id, following_id=user_id, date_created=datetime.now())
        db.session.add(new_follow)
        db.session.commit()
        create_notification(current_user.id, user_id, 'follow')
        
        return jsonify({'success': True, 'action': 'followed'})
        
    return jsonify({'success': False, 'message': 'Already following'})

@views.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow_user(user_id):
    follow_record = Follow.query.filter_by(follower_id=current_user.id, following_id=user_id).first()
    if follow_record:
        db.session.delete(follow_record)
        db.session.commit()
        return jsonify({'success': True, 'action': 'unfollowed'})
    return jsonify({'success': False, 'message': 'Not following'})

@views.route("/followers/<username>")
@login_required
def followers_list(username):
    user = User.query.filter_by(username=username).first_or_404()
    followers = User.query.join(Follow, Follow.follower_id == User.id)\
        .filter(Follow.following_id == user.id).all()
    following_ids = {f.following_id for f in Follow.query.filter_by(follower_id=current_user.id).all()}
    return render_template("followers.html", profile_user=user, users=followers, following_ids=following_ids, title="Followers")

@views.route("/following/<username>")
@login_required
def following_list(username):
    user = User.query.filter_by(username=username).first_or_404()
    following = User.query.join(Follow, Follow.following_id == User.id)\
        .filter(Follow.follower_id == user.id).all()
    following_ids = {f.following_id for f in Follow.query.filter_by(follower_id=current_user.id).all()}
    return render_template("followers.html", profile_user=user, users=following, following_ids=following_ids, title="Following")

# =================================================
# ACCOUNT DEACTIVATION
# =================================================

@views.route('/deactivate-account', methods=['POST'])
@login_required
def deactivate_account():
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

@views.route('/api/search-users')
@login_required
def api_search_users():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    users = User.query.filter(User.username.ilike(f"%{query}%")).limit(5).all()
    results = []
    for u in users:
        results.append({
            'username': u.username,
            'profile_pic': u.profile_pic
        })
    return jsonify(results)

@views.route("/search-page")
@login_required
def search():
    query = request.args.get('q', '').strip()
    
    users = User.query.filter(User.username.ilike(f"%{query}%")).all()
    posts = Post.query.filter(Post.text.ilike(f"%{query}%")).all()
    posts = enrich_posts(posts)
    
    suggestions = []
    
    if len(users) == 0:
        suggestions = User.query.order_by(func.random()).limit(3).all()
    else:
        suggestions = []

    return render_template(
        "search.html", 
        user=current_user, 
        users=users, 
        posts=posts, 
        suggestions=suggestions,
        query=query
    )

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
def update_cover_pic():
    if 'cover_pic' not in request.files:
        flash('No file provided.', category='error')
        return redirect(url_for('views.profile', username=current_user.username))
    
    file = request.files['cover_pic']
    
    if file.filename == '':
        flash('No selected file.', category='error')
        return redirect(url_for('views.profile', username=current_user.username))
        
    if file and allowed_file(file.filename):
        filename = compress_image(file, 'posts', width=1080, height=600)
        current_user.cover_pic = filename
        db.session.commit()
        flash('Cover photo updated!', category='success')
    else:
        flash('Invalid file type.', category='error')
        
    return redirect(url_for('views.profile', username=current_user.username))

@views.route("/like-comment/<comment_id>", methods=['POST'])
@login_required
def like_comment(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first()
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404

    like = CommentLike.query.filter_by(author=current_user.id, comment_id=comment_id).first()
    liked = False

    if like:
        db.session.delete(like)
        liked = False
    else:
        # ✅ FIX: Use Local Time
        like = CommentLike(author=current_user.id, comment_id=comment_id, date_created=datetime.now())
        db.session.add(like)
        liked = True

    db.session.commit()
    return jsonify({"likes": len(comment.likes), "liked": liked})

@views.route("/post/<id>")
def post_view(id):
    post = Post.query.get(id)
    
    if not post:
        flash('Post does not exist.', category='error')
        return redirect(url_for('views.home'))
    
    posts = enrich_posts([post])
    
    return render_template(
        "posts.html", 
        user=current_user, 
        posts=posts, 
        username=post.user.username,
        pagination=None 
    )

# =================================================
# MESSAGING SYSTEM (Inbox & Chat)
# =================================================

@views.route('/inbox')
@login_required
def inbox():
    messages = Message.query.filter(
        or_(Message.sender_id == current_user.id, Message.recipient_id == current_user.id)
    ).order_by(Message.date_created.desc()).all()
    
    conversations = {}
    
    for msg in messages:
        partner = msg.recipient if msg.sender_id == current_user.id else msg.sender
        if partner.id not in conversations:
            conversations[partner.id] = {
                'user': partner,
                'last_message': msg,
                'unread': (not msg.is_read and msg.recipient_id == current_user.id)
            }
    
    chats = list(conversations.values())
    return render_template("inbox.html", user=current_user, chats=chats)

@views.route('/api/send-message', methods=['POST'])
@login_required
def api_send_message():
    data = request.get_json()
    recipient_username = data.get('recipient')
    text = data.get('text')
    
    recipient = User.query.filter_by(username=recipient_username).first()
    if not recipient:
        return jsonify({'error': 'User not found'}), 404
        
    # ✅ FIX: Use Local Time
    msg = Message(
        sender_id=current_user.id, 
        recipient_id=recipient.id, 
        text=text,
        date_created=datetime.now()
    )
    db.session.add(msg)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'id': msg.id,
        'text': msg.text,
        'time': msg.date_created.strftime('%H:%M'),
        'sender_pic': current_user.profile_pic
    })
    
@views.route('/chat/<username>', methods=['GET']) 
@login_required
def chat(username):
    recipient = User.query.filter_by(username=username).first_or_404()
    
    if recipient.id == current_user.id:
        return redirect(url_for('views.inbox'))

    is_following = Follow.query.filter_by(follower_id=current_user.id, following_id=recipient.id).first()
    if not is_following:
        flash(f"You must follow {recipient.username} to message them.", category='error')
        return redirect(url_for('views.profile', username=username))

    unread_msgs = Message.query.filter_by(sender_id=recipient.id, recipient_id=current_user.id, is_read=False).all()
    for msg in unread_msgs:
        msg.is_read = True
    db.session.commit()

    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.recipient_id == recipient.id),
            (Message.sender_id == recipient.id) & (Message.recipient_id == current_user.id)
        )
    ).order_by(Message.date_created.asc()).all()

    return render_template("chat.html", user=current_user, recipient=recipient, messages=messages)

@views.route('/api/delete-message/<int:id>', methods=['POST'])
@login_required
def delete_message(id):
    msg = Message.query.get(id)
    
    if not msg:
        return jsonify({'error': 'Message not found'}), 404
        
    if msg.sender_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(msg)
    db.session.commit()
    
    return jsonify({'success': True})

# =================================================
# ERROR HANDLERS
# =================================================

@views.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html', user=current_user), 404

@views.app_errorhandler(500)
def internal_server_error(e):
    return render_template('500.html', user=current_user), 500

@views.route('/about')
def about():
    return render_template("about.html", user=current_user)