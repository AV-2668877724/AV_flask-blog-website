from functools import wraps
from flask import ( 
    Blueprint, render_template, request,
    flash, redirect, url_for, abort, jsonify, current_app
)
from flask_login import login_required, current_user
from .models import User, Post, Comment, Like, Follow
from sqlalchemy.exc import IntegrityError
from . import db
from sqlalchemy import func
import re, json, os, uuid
from werkzeug.utils import secure_filename
from sqlalchemy.orm.attributes import flag_modified

views = Blueprint('views', __name__)

# Security: Password required to perform Admin actions
ADMIN_ACTION_PASSWORD = "adminready777"

# Allowed Image Extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# =================================================
# UTILITY HELPERS
# =================================================

def allowed_file(filename):
    """Check if the file has a valid extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_picture(form_picture, folder_name="posts"):
    """
    Saves a file to static/uploads/{folder_name} with a unique random name.
    Returns the new filename.
    """
    # Generate a random hex to prevent filename collisions
    random_hex = str(uuid.uuid4().hex)[:8]
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    
    # Build the full path: website/static/uploads/{folder_name}/{filename}
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder_name)
    
    # Create directory if it doesn't exist
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)
        
    # Save the file
    file_path = os.path.join(upload_path, picture_fn)
    form_picture.save(file_path)
    
    return picture_fn

def enrich_posts(posts):
    """
    Adds auxiliary data to posts (like count, user liked status).
    Useful for creating a consistent object structure for templates.
    """
    for post in posts:
        post.likes_count = len(post.likes)
        post.liked = False
        if current_user.is_authenticated:
            post.liked = any(l.author == current_user.id for l in post.likes)
    return posts

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
    per_page = 5
    
    # Fetch posts, newest first
    pagination = Post.query.order_by(Post.date_created.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    posts = enrich_posts(pagination.items)

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
        
        # Check for cover image upload
        cover_image_file = request.files.get('cover_image')
        cover_image_name = None

        if not text:
            flash('Post content cannot be empty!', category='error')
        else:
            # Process Image if it exists
            if cover_image_file and allowed_file(cover_image_file.filename):
                cover_image_name = save_picture(cover_image_file, 'posts')
            
            # Save Post
            post = Post(text=text, author=current_user.id, cover_image=cover_image_name)
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
        
        # Check for new cover image
        cover_image_file = request.files.get('cover_image')
        
        if not text:
            flash("Post content cannot be empty.", category='error')
        else:
            post.text = text
            
            # Update image only if a new one is uploaded
            if cover_image_file and allowed_file(cover_image_file.filename):
                # Optional: Delete old image here if you want to save space
                new_filename = save_picture(cover_image_file, 'posts')
                post.cover_image = new_filename
                
            db.session.commit()
            flash("Post updated!", category='success')
            return redirect(url_for('views.home'))

    return render_template("edit_post.html", user=current_user, post=post)

@views.route("/delete-post/<id>")
@login_required
def delete_post(id):
    post = Post.query.filter_by(id=id).first()
    if not post:
        flash("Post does not exist.", category='error')
    elif current_user.id != post.author and not current_user.is_admin:
        flash("You do not have permission to delete this post.", category='error')
    else:
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted.', category='success')

    return redirect(url_for('views.home'))

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
            comment = Comment(text=text, author=current_user.id, post_id=post_id)
            db.session.add(comment)
            db.session.commit()
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
        # Soft delete (hide it)
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
        return jsonify({'error': 'Post not found'}, 404)

    liked = False
    if like:
        db.session.delete(like)
        db.session.commit()
    else:
        like = Like(author=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()
        liked = True

    return jsonify({
        "likes": len(post.likes), 
        "liked": liked
    })

# =================================================
# PROFILE & SETTINGS
# =================================================

@views.route("/profile/<username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('User not found.', category='error')
        return redirect(url_for('views.home'))

    page = request.args.get('page', 1, type=int)
    per_page = 5
    
    posts_pagination = Post.query.filter_by(author=user.id)\
        .order_by(Post.date_created.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
        
    posts = enrich_posts(posts_pagination.items)

    followers_count = Follow.query.filter_by(following_id=user.id).count()
    following_count = Follow.query.filter_by(follower_id=user.id).count()
    
    is_following = False
    if current_user.is_authenticated:
        is_following = Follow.query.filter_by(
            follower_id=current_user.id, 
            following_id=user.id
        ).first()

    return render_template(
        "profile.html", 
        user=current_user,
        profile_user=user,
        posts=posts,
        followers_count=followers_count,
        following_count=following_count,
        total_posts=posts_pagination.total,
        is_following=is_following,
        pagination=posts_pagination
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
        # Save to 'avatars' folder inside static/uploads
        filename = save_picture(file, 'avatars')
        
        # Update User Model
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

@views.route('/change-username', methods=['POST'])
@login_required
def change_username():
    new_username = request.form.get('username')
    
    # Validation
    if not new_username or len(new_username) < 3:
        flash("Username too short.", category='error')
    elif not re.match("^[a-zA-Z0-9_.]+$", new_username):
        flash("Username can only contain letters, numbers, dots, and underscores.", category='error')
    else:
        existing = User.query.filter_by(username=new_username).first()
        if existing:
            flash("Username already taken.", category='error')
        else:
            current_user.username = new_username
            db.session.commit()
            flash("Username updated! Please login again.", category='success')
            # Logout logic could go here, but usually nice to keep them logged in or redirect to logout
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
        
        # We need a copy of the dictionary to modify it safely
        current_links = dict(current_user.social_links) if current_user.social_links else {}
        
        # Handle multiple links of same platform (e.g., twitter_1, twitter_2)
        key = platform
        counter = 1
        while key in current_links:
            key = f"{platform}_{counter}"
            counter += 1
            
        current_links[key] = link
        
        # Force SQLAlchemy to detect change in JSON column
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
    active_posts = Post.query.all() # Hard delete model implies all posts are active
    comments = Comment.query.order_by(Comment.date_created.desc()).limit(50).all()
    
    # Since we are using hard deletes for Posts in this phase, deleted_posts is empty
    # unless you have a separate Archive model. Passing empty list for safety.
    deleted_posts = []

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
    if pwd != ADMIN_ACTION_PASSWORD:
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

@views.route('/admin/delete-post/<int:post_id>', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    if not current_user.is_admin:
        abort(403)
        
    pwd = request.form.get('admin_password')
    if pwd != ADMIN_ACTION_PASSWORD:
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    post = Post.query.get(post_id)
    if post:
        db.session.delete(post)
        db.session.commit()
        flash("Post deleted.", category='success')
    
    return redirect(url_for('views.admin_dashboard'))

@views.route('/admin/delete-comment/<int:comment_id>', methods=['POST'])
@login_required
def admin_delete_comment(comment_id):
    if not current_user.is_admin:
        abort(403)
        
    pwd = request.form.get('admin_password')
    if pwd != ADMIN_ACTION_PASSWORD:
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
    if pwd != ADMIN_ACTION_PASSWORD:
        flash("Incorrect admin password", category='error')
        return redirect(url_for('views.admin_dashboard'))
        
    comment = Comment.query.get(comment_id)
    if comment:
        comment.is_deleted = False
        db.session.commit()
        flash("Comment restored.", category='success')
        
    return redirect(url_for('views.admin_dashboard'))
    
# =================================================
# SEARCH & FOLLOW
# =================================================

@views.route("/search")
@login_required
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('views.home'))
        
    # Search Users
    users = User.query.filter(User.username.ilike(f"%{query}%")).all()
    
    # Search Posts
    posts = Post.query.filter(Post.text.ilike(f"%{query}%")).all()
    posts = enrich_posts(posts)
    
    return render_template("search.html", user=current_user, users=users, posts=posts, query=query)

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
        new_follow = Follow(follower_id=current_user.id, following_id=user_id)
        db.session.add(new_follow)
        db.session.commit()
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
@views.route('/about')
def about():
    return render_template("about.html", user=current_user)