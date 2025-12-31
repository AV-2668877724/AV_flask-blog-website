from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, login_required, logout_user, current_user
from . import db
from werkzeug.security import check_password_hash, generate_password_hash
from .models import User

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = (request.form.get('login') or "").strip()
        password = request.form.get('password')

        user = None
        login_type = None

        if "@" in login_input:
            user = User.query.filter_by(email=login_input).first()
            login_type = "email"
        else:
            user = User.query.filter_by(username=login_input).first()
            login_type = "username"

        if not user:
            flash(
                "No account found with that email address." if login_type == "email"
                else "No account found with that username.",
                category="error"
            )
        elif not check_password_hash(user.password, password):
            flash("Incorrect password. Please try again.", category="error")
        else:
            login_user(user, remember=True)
            flash("Logged in successfully!", category="success")
            return redirect(url_for("views.home"))

    return render_template("login.html")


@auth.route('/sign-up', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password1 = request.form.get('password1') or ''
        password2 = request.form.get('password2') or ''
        dob = (request.form.get('dob') or '').strip().lower()
        fav_person = (request.form.get('fav_person') or '').strip().lower()

        email_exists = User.query.filter_by(email=email).first()
        username_exists = User.query.filter_by(username=username).first()

        if email_exists:
            flash('Email already exists.', category='error')
        elif username_exists:
            flash('Username already exists.', category='error')
        elif password1 != password2:
            flash('Passwords do not match.', category='error')
        elif len(username) < 2:
            flash('Username is too short.', category='error')
        elif len(password1) < 6:
            flash('Password is too short.', category='error')
        elif len(email) < 4 or '@' not in email:
            flash('Email is invalid!', category='error')
        elif not dob or not fav_person:
            flash('Security questions are required.', category='error')
        else:
            try:
                new_user = User(
                    email=email,
                    username=username,
                    password=generate_password_hash(password1, method='pbkdf2:sha256'),
                    dob_hash=generate_password_hash(dob, method='pbkdf2:sha256'),
                    fav_person_hash=generate_password_hash(fav_person, method='pbkdf2:sha256')
                )
                db.session.add(new_user)
                db.session.commit()

                login_user(new_user, remember=True)
                flash('Account created successfully!', category='success')
                return redirect(url_for('views.home'))

            except Exception as e:
                db.session.rollback()
                print(f"[SIGNUP ERROR] {str(e)}")
                flash('An error occurred while creating your account. Please try again.', category='error')

    return render_template("signup.html")


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        dob = (request.form.get('dob') or '').strip().lower()
        fav_person = (request.form.get('fav_person') or '').strip().lower()
        new_password = request.form.get('new_password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Email not found.', category='error')
        elif not check_password_hash(user.dob_hash, dob):
            flash('Date of birth does not match.', category='error')
        elif not check_password_hash(user.fav_person_hash, fav_person):
            flash('Favorite person does not match.', category='error')
        elif new_password != confirm_password:
            flash('Passwords do not match.', category='error')
        elif len(new_password) < 6:
            flash('New password is too short.', category='error')
        else:
            try:
                user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
                db.session.commit()
                flash('Password reset successful! Please login with your new password.', category='success')
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.session.rollback()
                print(f"[FORGOT PASSWORD ERROR] {str(e)}")
                flash('An error occurred while resetting your password. Please try again.', category='error')

    return render_template("forgot_password.html")


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.home'))
