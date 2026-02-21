from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, mail
from flask_login import login_user, login_required, logout_user, current_user
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import random
import string
from flask import session
import os
import re 
from datetime import datetime 
from threading import Thread
from sqlalchemy import func

auth = Blueprint('auth', __name__)

# Setup Token Serializer
s = URLSafeTimedSerializer('CCAV@129') 

RESERVED_USERNAMES = {
    'avpostory','av_postory','home', 'login', 'logout', 'sign-up', 'signup', 'register',
    'inbox', 'chat', 'messages', 'notifications', 'search', 'explore',
    'admin', 'dashboard', 'settings', 'profile', 'user', 'users',
    'static', 'assets', 'uploads', 'images', 'css', 'js',
    'api', 'about', 'contact', 'help', 'support', 'terms', 'privacy',
    'create-post', 'edit-post', 'delete', 'update', 'deactivate'
}

# ==========================================
#  HELPER: SEND EMAILS (ASYNC)
# ==========================================
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def get_public_link(endpoint, token):
    """Generates a link and forces the Ngrok URL if running locally."""
    link = url_for(endpoint, token=token, _external=True)
    
    # YOUR NGROK URL (Update this if it changes!)
    PUBLIC_DOMAIN = "https://arjun-diffusible-nonfamiliarly.ngrok-free.dev"
    
    if "127.0.0.1" in link or "localhost" in link:
        link = link.replace("http://127.0.0.1:8000", PUBLIC_DOMAIN)
        link = link.replace("http://localhost:8000", PUBLIC_DOMAIN)
        
    return link

def send_verification_email(user_email):
    token = s.dumps(user_email, salt='email-confirm')
    link = get_public_link('auth.confirm_email', token)
    
    sender_email = os.getenv('MAIL_USERNAME')
    msg = Message('Confirm Your Email - AV Postory', 
                  sender=sender_email, 
                  recipients=[user_email])
    
    msg.body = f'Your link is: {link}\n\nThis link expires in 1 hour.'
    
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

def send_reset_email(user_email):
    token = s.dumps(user_email, salt='password-reset')
    link = get_public_link('auth.reset_token', token)
    
    sender_email = os.getenv('MAIL_USERNAME')
    msg = Message('Password Reset Request', 
                  sender=sender_email, 
                  recipients=[user_email])
    
    msg.body = f'To reset your password, click the following link: {link}'
    
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()


# ==========================================
#  STEP 1: ENTER EMAIL
# ==========================================
@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered. Please log in.', category='error')
            return redirect(url_for('auth.login'))
        
        otp = ''.join(random.choices(string.digits, k=6))
        session['signup_email'] = email
        session['signup_otp'] = otp
        
        try:
            sender_email = os.getenv('MAIL_USERNAME')
            msg = Message('Your Verification Code - AV Postory', 
                  sender=sender_email, 
                  recipients=[email])
            msg.body = f'Your verification code is: {otp}\n\nDo not share this code.'
            Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()
            
            flash('OTP sent to your email!', category='success')
            return redirect(url_for('auth.verify_otp'))
        except Exception as e:
            print(e)
            flash('Error sending email. Check your internet connection.', category='error')

    return render_template("signup.html", user=current_user)

# ==========================================
#  STEP 2: VERIFY OTP
# ==========================================
@auth.route('/sign-up/verify', methods=['GET', 'POST'])
def verify_otp():
    if 'signup_email' not in session:
        return redirect(url_for('auth.sign_up'))
        
    if request.method == 'POST':
        user_otp = request.form.get('otp')
        generated_otp = session.get('signup_otp')
        
        if user_otp == generated_otp:
            session['email_verified'] = True
            flash('Email verified successfully!', category='success')
            return redirect(url_for('auth.finish_signup'))
        else:
            flash('Invalid OTP. Please try again.', category='error')
            
    return render_template("verify_otp.html", email=session['signup_email'], user=current_user)

# ==========================================
#  CHECK USERNAME (API)
# ==========================================
@auth.route('/check-username-signup', methods=['POST'])
def check_username_signup():
    data = request.json
    username = data.get('username', '').strip().lower()

    if not username or len(username) < 3:
        return jsonify({'available': False, 'message': 'Too short (min 3 chars).'})

    if not re.match("^[a-z0-9_.]+$", username):
         return jsonify({'available': False, 'message': 'Use only letters, numbers, . and _'})

    if username in RESERVED_USERNAMES:
        return jsonify({'available': False, 'message': 'This username is reserved.'})

    user = User.query.filter(func.lower(User.username) == username).first()
    
    if user:
        return jsonify({'available': False, 'message': 'Username is already taken.'})
    
    session['verified_username'] = username
    return jsonify({'available': True, 'message': 'Username is available!'})

# ==========================================
#  STEP 3: FINISH SIGNUP
# ==========================================
@auth.route('/sign-up/finish', methods=['GET', 'POST'])
def finish_signup():
    if not session.get('email_verified'):
        return redirect(url_for('auth.sign_up'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = session.get('signup_email')
        
        verified_username = session.get('verified_username')
        if not verified_username or verified_username != username.lower():
            flash('Please check username availability first.', category='error')
            return render_template('signup_final.html', user=current_user)
        
        if len(username) < 2:
            flash('Username must be greater than 1 character.', category='error')
        elif not re.match("^[a-zA-Z0-9_.]+$", username):
            flash("Username can only contain letters, numbers, dots (.), and underscores (_). No spaces.", category='error')
        elif password != confirm_password:
            flash('Passwords don\'t match.', category='error')
        elif len(password) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            existing_user = User.query.filter(func.lower(User.username) == username.lower()).first()
            if existing_user:
                flash('Username is already taken.', category='error')
                return render_template('signup_final.html', user=current_user)

            new_user = User(email=email, username=username, 
                            password=generate_password_hash(password, method='scrypt'), 
                            is_verified=True,
                            date_created=datetime.now())
            
            db.session.add(new_user)
            db.session.commit()
            
            login_user(new_user, remember=True)
            
            session.pop('signup_email', None)
            session.pop('signup_otp', None)
            session.pop('email_verified', None)
            
            flash('Account created successfully!', category='success')
            return redirect(url_for('views.home'))

    return render_template("signup_final.html", user=current_user)

# ==========================================
#  LOGIN & LOGOUT
# ==========================================
@auth.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_verified = True
            db.session.commit()
            flash('Email verified! You can now login.', category='success')
        else:
            flash('User not found.', category='error')
    except SignatureExpired:
        flash('The token is expired.', category='error')
    except Exception:
        flash('The token is invalid.', category='error')
    return redirect(url_for('auth.login'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                if user.is_active is False:
                    return render_template("account_deactivated.html", username=user.username, email=user.email)

                if not user.is_verified:
                    flash('Please verify your email first.', category='error')
                    return render_template("login.html", user=current_user)

                user.last_login = datetime.now()
                db.session.commit()

                login_user(user, remember=True)
                flash('Logged in successfully!', category='success')
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template("login.html", user=current_user)

@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            send_reset_email(email)
            flash('An email has been sent with instructions to reset your password.', category='success')
            return redirect(url_for('auth.login'))
        else:
            flash('No account found with that email.', category='error')
    return render_template('reset_request.html', user=current_user)

# ==========================================
#  RESET TOKEN (Fixed Auto-Logout & Password Check)
# ==========================================
@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    # Force Logout if user clicks reset link while logged in
    if current_user.is_authenticated:
        logout_user()
        flash('Logged out for security. Please create your new password.', category='info')
        
    try:
        email = s.loads(token, salt='password-reset', max_age=1800)
    except SignatureExpired:
        flash('The token is expired.', category='error')
        return redirect(url_for('auth.reset_request'))
    except Exception:
        flash('Invalid token.', category='error')
        return redirect(url_for('auth.reset_request'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', category='error')
        elif len(password) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            user = User.query.filter_by(email=email).first()
            if user:
                # ✅ FIX: Check if the new password is the exact same as their current password
                if check_password_hash(user.password, password):
                    flash('Your new password cannot be the same as your current password. Please choose a different one.', category='error')
                else:
                    # Password is new and valid, save it!
                    user.password = generate_password_hash(password, method='scrypt')
                    db.session.commit()
                    flash('Your password has been updated! You can now login.', category='success')
                    return redirect(url_for('auth.login'))

    return render_template('reset_token.html', token=token, user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))