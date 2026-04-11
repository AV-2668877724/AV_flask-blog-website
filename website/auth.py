from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from .models import User, Message as ChatMessage 
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, mail, limiter 
from flask_login import login_user, login_required, logout_user, current_user
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import random
import string
from flask import session
import os
import re 
from datetime import datetime 
from sqlalchemy import func

# 🚀 NEW: Import ThreadPoolExecutor for our lightweight Email Task Queue
from concurrent.futures import ThreadPoolExecutor

auth = Blueprint('auth', __name__)

# 🚀 NEW: Initialize the Global Email Queue (Max 5 background workers running concurrently)
email_executor = ThreadPoolExecutor(max_workers=5)

# Setup Token Serializer dynamically using the app's secret key
def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

RESERVED_USERNAMES = {
    'avpostory','av_postory','home', 'login', 'logout', 'sign-up', 'signup', 'register',
    'inbox', 'chat', 'messages', 'notifications', 'search', 'explore',
    'admin', 'dashboard', 'settings', 'profile', 'user', 'users',
    'static', 'assets', 'uploads', 'images', 'css', 'js',
    'api', 'about', 'contact', 'help', 'support', 'terms', 'privacy',
    'create-post', 'edit-post', 'delete', 'update', 'deactivate'
}

# ==========================================
#  HELPER: SEND EMAILS (ASYNC WORKER)
# ==========================================
def send_async_email(app, msg):
    """ This function is safely executed by the background ThreadPoolExecutor """
    with app.app_context():
        try:
            mail.send(msg)
            print("✅ EMAIL SENT SUCCESSFULLY TO:", msg.recipients)
        except Exception as e:
            print("=========================================")
            print("❌ CRITICAL EMAIL ERROR:")
            print(e)
            print("=========================================")

def get_public_link(endpoint, token=None, **kwargs):
    """Generates a link and forces the Production URL if running locally/behind proxy."""
    if token:
        kwargs['token'] = token
    link = url_for(endpoint, _external=True, **kwargs)
    
    # 🚀 FIX: Pull the domain from .env instead of hardcoding it
    PUBLIC_DOMAIN = os.getenv("PUBLIC_DOMAIN") 
    
    # Only replace if a PUBLIC_DOMAIN is explicitly set in your .env file
    if PUBLIC_DOMAIN:
        link = re.sub(r'https?://(127\.0\.0\.1|localhost)(:\d+)?', PUBLIC_DOMAIN, link)
        
    return link

def send_verification_email(user_email):
    token = get_serializer().dumps(user_email, salt='email-confirm')
    link = get_public_link('auth.confirm_email', token=token)
    
    sender_email = os.getenv('MAIL_USERNAME')
    msg = Message('Confirm Your Email - AV Postory', 
                  sender=sender_email, 
                  recipients=[user_email],
                  reply_to='noreply@avpostory.com')
    
    msg.body = f'Your link is: {link}\n\nThis link expires in 1 hour.'
    
    # 🚀 NEW: Queue the email instead of using threading.Thread
    email_executor.submit(send_async_email, current_app._get_current_object(), msg)


def send_reset_email(user_email):
    token = get_serializer().dumps(user_email, salt='password-reset')
    link = get_public_link('auth.forgot_password_token', token=token) 
    
    sender_email = os.getenv('MAIL_USERNAME')
    msg = Message('Password Reset Request - AV Postory', 
                  sender=sender_email, 
                  recipients=[user_email],
                  reply_to='noreply@avpostory.com')
                  
    logo_url = "https://res.cloudinary.com/dkpfw99ul/image/upload/v1773030390/av_postory/assets/main_logo.png" 
    
    current_year = datetime.utcnow().year
    
    msg.body = f'''To reset your password, click the following link: {link}\nIf you did not request this, please ignore this email.'''

    msg.html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Inter', Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; line-height: 1.6; padding: 20px; margin: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; padding: 40px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }}
            .logo {{ text-align: center; margin-bottom: 30px; }}
            .logo img {{ max-height: 70px; border-radius: 8px; }}
            h1 {{ color: #4f46e5; font-size: 24px; text-align: center; margin-bottom: 20px; font-weight: 700; }}
            p {{ font-size: 16px; color: #475569; margin-bottom: 20px; text-align: center; }}
            .btn-container {{ text-align: center; margin-top: 35px; margin-bottom: 35px; }}
            .btn {{ background: linear-gradient(135deg, #4f46e5, #4338ca); color: #ffffff !important; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 16px; display: inline-block; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25); }}
            .footer {{ text-align: center; font-size: 13px; color: #94a3b8; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <img src="{logo_url}" alt="AV Postory Logo">
            </div>
            
            <h1>Reset Your Password</h1>
            
            <p>We received a request to reset your password for your AV Postory account. Click the button below to choose a new password.</p>
            
            <div class="btn-container">
                <a href="{link}" class="btn">Reset Password</a>
            </div>

            <p style="font-size: 14px;">If you did not request a password reset, you can safely ignore this email. Your account is completely secure and no changes will be made.<br><br>Please note: This link will expire in 10 minutes.</p>

            <div class="footer">
                &copy; {current_year} AV Postory. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    # 🚀 NEW: Queue the email instead of using threading.Thread
    email_executor.submit(send_async_email, current_app._get_current_object(), msg)

def send_welcome_email(user_email, username):
    sender_email = os.getenv('MAIL_USERNAME')
    msg = Message('Welcome to AV Postory! 🎉', 
                  sender=sender_email, 
                  recipients=[user_email],
                  reply_to='noreply@avpostory.com')
    
    logo_url = "https://res.cloudinary.com/dkpfw99ul/image/upload/v1773030390/av_postory/assets/main_logo.png"
    
    login_url = get_public_link('auth.login')
    current_year = datetime.utcnow().year
    
    msg.body = f'''Hello {username},\nWelcome to AV Postory! Go to AV Postory: {login_url}'''

    msg.html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Inter', Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; line-height: 1.6; padding: 20px; margin: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; padding: 40px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }}
            .logo {{ text-align: center; margin-bottom: 30px; }}
            .logo img {{ max-height: 70px; border-radius: 8px; }}
            h1 {{ color: #4f46e5; font-size: 26px; text-align: center; margin-bottom: 20px; font-weight: 700; }}
            p {{ font-size: 16px; color: #475569; margin-bottom: 20px; }}
            .highlight-box {{ background-color: #f1f5f9; padding: 25px; border-radius: 12px; margin-bottom: 30px; border-left: 4px solid #4f46e5; }}
            .highlight-box p {{ margin-top: 0; font-weight: 600; color: #0f172a; }}
            .highlight-box ul {{ margin: 0; padding-left: 20px; }}
            .highlight-box li {{ margin-bottom: 12px; color: #334155; }}
            .highlight-box li strong {{ color: #0f172a; }}
            .btn-container {{ text-align: center; margin-top: 35px; margin-bottom: 35px; }}
            .btn {{ background: linear-gradient(135deg, #4f46e5, #4338ca); color: #ffffff !important; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 16px; display: inline-block; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25); }}
            .footer {{ text-align: center; font-size: 13px; color: #94a3b8; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <img src="{logo_url}" alt="AV Postory Logo">
            </div>
            
            <h1>Welcome to AV Postory, {username}! 🎉</h1>
            
            <p>We are absolutely thrilled to have you join our community.</p>
            
            <p><strong>AV Postory</strong> is a next-generation social publishing platform designed for clarity and connection. We provide a distraction-free environment where writers, developers, and thinkers can share their stories, code, and ideas with a community that cares.</p>
            
            <div class="highlight-box">
                <p>Ready to get started? Here is what you can do next:</p>
                <ul>
                    <li><strong>Complete your profile:</strong> Add a bio, profile picture, and your social links to let people know who you are.</li>
                    <li><strong>Browse the feed:</strong> Discover interesting stories and perspectives from other creators.</li>
                    <li><strong>Connect:</strong> Follow users you find interesting and engage via real-time chat.</li>
                    <li><strong>Share your voice:</strong> Write and publish your very first story.</li>
                </ul>
            </div>

            <div class="btn-container">
                <a href="{login_url}" class="btn">Go to your Dashboard</a>
            </div>

            <p>If you have any questions, feedback, or need help navigating the platform, simply reply to this email. We are always here to help!</p>
            
            <p>Best regards,<br><strong style="color: #0f172a;">The AV Postory Team</strong></p>

            <div class="footer">
                &copy; {current_year} AV Postory. All rights reserved.<br>
                You are receiving this email because you recently created an account on our platform.
            </div>
        </div>
    </body>
    </html>
    """
    
    # 🚀 NEW: Queue the email instead of using threading.Thread
    email_executor.submit(send_async_email, current_app._get_current_object(), msg)


# ==========================================
#  STEP 1: ENTER EMAIL
# ==========================================
@auth.route('/sign-up', methods=['GET', 'POST'])
@limiter.limit("10 per hour") 
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
            
            # 🚀 NEW: Queue the email instead of using threading.Thread
            email_executor.submit(send_async_email, current_app._get_current_object(), msg)
            
            flash('OTP sent to your email!', category='success')
            return redirect(url_for('auth.verify_otp'))
        except Exception as e:
            print(e)
            flash('Error queuing email. Please try again.', category='error')

    return render_template("signup.html", user=current_user)

# ==========================================
#  STEP 2: VERIFY OTP
# ==========================================
@auth.route('/sign-up/verify', methods=['GET', 'POST'])
@limiter.limit("15 per hour") 
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
@limiter.limit("30 per minute") 
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
@limiter.limit("5 per hour") 
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
                            date_created=datetime.utcnow())
            
            db.session.add(new_user)
            db.session.commit()
            
            try:
                send_welcome_email(email, username)
            except Exception as e:
                print("Failed to queue welcome email:", e)
            
            login_user(new_user, remember=True)
            
            session.pop('signup_email', None)
            session.pop('signup_otp', None)
            session.pop('email_verified', None)
            
            flash('Welcome to AV Postory! Your account is ready.', category='signup_success')
            return redirect(url_for('views.home'))

    return render_template("signup_final.html", user=current_user)

# ==========================================
#  LOGIN & LOGOUT
# ==========================================
@auth.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = get_serializer().loads(token, salt='email-confirm', max_age=3600)
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
@limiter.limit("20 per minute") 
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

                user.last_login = datetime.utcnow()
                db.session.commit()

                login_user(user, remember=True)
                flash('Logged in successfully!', category='success')
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template("login.html", user=current_user)

# ==========================================
#  FORGOT PASSWORD ROUTES
# ==========================================
@auth.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per hour") 
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            send_reset_email(email)
            
        flash('If an account with that email exists, a password reset link has been sent.', category='info')
        return redirect(url_for('auth.login'))
        
    return render_template('reset_request.html', user=current_user)

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per hour") 
def forgot_password_token(token):
    if current_user.is_authenticated:
        logout_user()
        flash('Logged out for security. Please create your new password.', category='info')
        
    try:
        email = get_serializer().loads(token, salt='password-reset', max_age=600)
    except SignatureExpired:
        flash('The password reset link is expired.', category='error')
        return redirect(url_for('auth.forgot_password'))
    except Exception:
        flash('Invalid password reset token.', category='error')
        return redirect(url_for('auth.forgot_password'))

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
                if check_password_hash(user.password, password):
                    flash('Your new password cannot be the same as your current password.', category='error')
                else:
                    user.password = generate_password_hash(password, method='scrypt')
                    db.session.commit()
                    flash('Your password has been successfully updated! You can now log in.', category='success')
                    return redirect(url_for('auth.login'))
            else:
                flash('User not found.', category='error')
                return redirect(url_for('auth.forgot_password'))

    return render_template('reset_token.html', token=token, user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))