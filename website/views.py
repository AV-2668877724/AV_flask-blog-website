from functools import wraps
from flask import ( 
    Blueprint, render_template, request,
    flash, redirect, url_for, abort, jsonify
)
from flask_login import login_required, current_user
from .models import User, Post, Comment, Like
from . import db
from sqlalchemy import func
import re

views = Blueprint('views', __name__)

ADMIN_ACTION_PASSWORD = "adminready777"

# =================================================
# UTILITY HELPERS
# =================================================

def enrich_posts(posts, current_user_id):
    """Convert Post objects → dicts with likes info"""
    enriched = []
    for p in posts:
        likes_count = len(p.likes)
        liked = any(l.author == current_user_id for l in p.likes)
        enriched.append({
            "id": p.id,
            "text": p.text,
            "date_created": p.date_created,
            "author": p.author,
            "user": p.user,
            "comments": p.comments,
            "likes_count": likes_count,
            "liked": liked
        })
    return enriched


# =================================================
# ADMIN DECORATOR & PASSWORD CHECK
# =================================================

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def verify_admin_password():
    password = request.form.get("admin_password")
    if password != ADMIN_ACTION_PASSWORD:
        flash("Invalid admin password. Action denied.", "error")
        return False
    return True


# =================================================
# ADMIN ACTIONS
# =================================================

@views.route("/admin/delete-post/<int:post_id>", methods=["POST"])
@login_required
@admin_required
def admin_delete_post(post_id):
    if not verify_admin_password():
        return redirect(url_for("views.admin_dashboard"))

    post = Post.query.get_or_404(post_id)
    post.is_deleted = True
    db.session.commit()
    flash("Post deleted successfully.", "success")
    return redirect(url_for("views.admin_dashboard"))


@views.route("/admin/restore-post/<int:post_id>", methods=["POST"])
@login_required
@admin_required
def admin_restore_post(post_id):
    if not verify_admin_password():
        return redirect(url_for("views.admin_dashboard"))

    post = Post.query.filter_by(id=post_id, is_deleted=True).first_or_404()
    post.is_deleted = False
    db.session.commit()
    flash("Post restored successfully.", "success")
    return redirect(url_for("views.admin_dashboard"))


@views.route("/admin/delete-user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def admin_delete_user(user_id):
    if not verify_admin_password():
        return redirect(url_for("views.admin_dashboard"))

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot delete yourself.", "error")
    else:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully.", "success")

    return redirect(url_for("views.admin_dashboard"))


@views.route("/admin/delete-comment/<int:comment_id>", methods=["POST"])
@login_required
@admin_required
def admin_delete_comment(comment_id):
    if not verify_admin_password():
        return redirect(url_for("views.admin_dashboard"))

    comment = Comment.query.get_or_404(comment_id)
    comment.is_deleted = True
    db.session.commit()
    flash("Comment deleted successfully.", "success")
    return redirect(url_for("views.admin_dashboard"))


@views.route("/admin/restore-comment/<int:comment_id>", methods=["POST"])
@login_required
@admin_required
def admin_restore_comment(comment_id):
    if not verify_admin_password():
        return redirect(url_for("views.admin_dashboard"))

    comment = Comment.query.filter_by(id=comment_id, is_deleted=True).first_or_404()
    comment.is_deleted = False
    db.session.commit()
    flash("Comment restored successfully.", "success")
    return redirect(url_for("views.admin_dashboard"))


# =================================================
# ADMIN DASHBOARD
# =================================================

@views.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    return render_template(
        "admin_dashboard.html",
        users=User.query.order_by(User.date_created.desc()).all(),
        active_posts=Post.query.filter_by(is_deleted=False).order_by(Post.date_created.desc()).all(),
        deleted_posts=Post.query.filter_by(is_deleted=True).order_by(Post.date_created.desc()).all(),
        comments=Comment.query.order_by(Comment.date_created.desc()).limit(50).all(),
        is_home=False
    )


# =================================================
# MAIN ROUTES
# =================================================

@views.route("/")
@views.route("/home")
@login_required
def home():
    page = request.args.get("page", 1, type=int)

    pagination = (
        Post.query
        .filter_by(is_deleted=False)
        .order_by(Post.date_created.desc())
        .paginate(page=page, per_page=5, error_out=False)
    )

    posts = enrich_posts(pagination.items, current_user.id)

    return render_template(
        "home.html",
        posts=posts,
        pagination=pagination,
        is_home=True
    )


@views.route("/create-post", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if not text:
            flash("Post cannot be empty!", "error")
        else:
            post = Post(text=text, author=current_user.id)
            db.session.add(post)
            db.session.commit()
            flash("Post created!", "success")
            return redirect(url_for("views.home"))

    return render_template("create_posts.html", is_home=False)


@views.route("/edit-post/<int:id>", methods=["GET", "POST"])
@login_required
def edit_post(id):
    post = Post.query.filter_by(id=id, is_deleted=False).first_or_404()

    if post.author != current_user.id:
        flash("Permission denied.", "error")
        return redirect(url_for("views.home"))

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if not text:
            flash("Post cannot be empty!", "error")
        else:
            post.text = text
            db.session.commit()
            flash("Post updated!", "success")
            return redirect(url_for("views.home"))

    return render_template("edit_post.html", post=post, is_home=False)


@views.route("/delete-post/<int:id>")
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)

    if post.author != current_user.id and not current_user.is_admin:
        flash("Permission denied.", "error")
    else:
        post.is_deleted = True
        db.session.commit()
        flash("Post deleted.", "success")

    return redirect(url_for("views.home"))


@views.route("/posts/<username>")
@login_required
def posts(username):
    user = User.query.filter_by(username=username).first_or_404()

    page = request.args.get("page", 1, type=int)
    pagination = (
        Post.query
        .filter_by(author=user.id, is_deleted=False)
        .order_by(Post.date_created.desc())
        .paginate(page=page, per_page=5, error_out=False)
    )

    posts = enrich_posts(pagination.items, current_user.id)

    return render_template(
        "posts.html",
        posts=posts,
        pagination=pagination,
        is_home=False
    )


# =================================================
# COMMENTS & LIKES
# =================================================

@views.route("/create-comment/<int:post_id>", methods=["POST"])
@login_required
def create_comment(post_id):
    text = request.form.get("text", "").strip()
    if not text:
        flash("Comment cannot be empty.", "error")
    else:
        comment = Comment(text=text, author=current_user.id, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        flash("Comment added!", "success")

    return redirect(url_for("views.home"))


@views.route("/delete-comment/<int:comment_id>")
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if comment.author != current_user.id and not current_user.is_admin:
        flash("Permission denied.", "error")
    else:
        comment.is_deleted = True
        db.session.commit()
        flash("Comment deleted.", "success")

    return redirect(url_for("views.home"))


@views.route("/like-post/<int:post_id>", methods=["POST"])
@login_required
def like_post(post_id):
    post = Post.query.filter_by(id=post_id, is_deleted=False).first_or_404()

    like = Like.query.filter_by(author=current_user.id, post_id=post_id).first()

    if like:
        db.session.delete(like)
    else:
        db.session.add(Like(author=current_user.id, post_id=post_id))

    db.session.commit()

    return jsonify({
        "likes": len(post.likes),
        "liked": any(l.author == current_user.id for l in post.likes)
    })


# =================================================
# USER PROFILE
# =================================================

@views.route("/profile/<username>")
@login_required
def profile(username):
    profile_user = User.query.filter_by(username=username).first_or_404()

    raw_posts = (
        Post.query
        .filter_by(author=profile_user.id, is_deleted=False)
        .order_by(Post.date_created.desc())
        .all()
    )

    posts = enrich_posts(raw_posts, current_user.id)

    total_posts = len(raw_posts)
    total_likes = (
        db.session.query(func.count(Like.id))
        .join(Post, Like.post_id == Post.id)
        .filter(Post.author == profile_user.id)
        .scalar()
    ) or 0

    return render_template(
        "profile.html",
        profile_user=profile_user,
        posts=posts,
        total_posts=total_posts,
        total_likes=total_likes,
        is_home=False,
        hide_dividers=True
    )

@views.route("/profile/edit-bio", methods=["POST"])
@login_required
def edit_bio():
    bio = request.form.get("bio", "").strip()

    if len(bio) > 300:
        flash("Bio must be under 300 characters.", "error")
        return redirect(url_for("views.profile", username=current_user.username))

    current_user.bio = bio
    db.session.commit()

    flash("Bio updated successfully.", "success")
    return redirect(url_for("views.profile", username=current_user.username))

@views.route("/profile/change-username", methods=["POST"])
@login_required
def change_username():
    new_username = request.form.get("username", "").strip()

    if not re.match(r"^[A-Za-z0-9_]{3,20}$", new_username):
        flash(
            "Username must be 3–20 characters (letters, numbers, underscore).",
            "error"
        )
        return redirect(url_for("views.profile", username=current_user.username))

    existing = User.query.filter_by(username=new_username).first()
    if existing:
        flash("Username already taken.", "error")
        return redirect(url_for("views.profile", username=current_user.username))

    current_user.username = new_username
    db.session.commit()

    flash("Username changed successfully. Please login again.", "success")
    return redirect(url_for("auth.logout"))

@views.route('/check-username', methods=['POST'])
@login_required
def check_username():
    data = request.get_json()
    username = data.get('username', '').strip()

    if not username:
        return jsonify({'available': False, 'message': 'Username required'})

    # Same username as current → allow
    if username == current_user.username:
        return jsonify({'available': True, 'message': 'This is already your username'})

    # Check DB
    exists = User.query.filter_by(username=username).first()

    if exists:
        return jsonify({'available': False, 'message': 'Username already taken'})
    else:
        return jsonify({'available': True, 'message': 'Username is available'})


# =================================================
# ABOUT
# =================================================

@views.route("/about")
def about():
    return render_template("about.html", is_home=False)
