from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
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
import re # ✅ Added Regex for username validation
from datetime import datetime # ✅ Added for Local Time login tracking

auth = Blueprint('auth', __name__)

# Setup Token Serializer
s = URLSafeTimedSerializer('CCAV@129') 

# ==========================================
#  HELPER: SEND EMAILS
# ==========================================
def send_verification_email(user_email):
    token = s.dumps(user_email, salt='email-confirm')
    link = url_for('auth.confirm_email', token=token, _external=True)
    
    sender_email = os.getenv('MAIL_USERNAME')
    
    msg = Message('Confirm Your Email - AV Postory', 
                  sender=sender_email, 
                  recipients=[user_email])
    
    msg.body = f'Your link is: {link}\n\nThis link expires in 1 hour.'
    mail.send(msg)

def send_reset_email(user_email):
    token = s.dumps(user_email, salt='password-reset')
    link = url_for('auth.reset_token', token=token, _external=True)
    
    sender_email = os.getenv('MAIL_USERNAME')
    
    msg = Message('Password Reset Request', 
                  sender=sender_email, 
                  recipients=[user_email])
    
    msg.body = f'To reset your password, click the following link: {link}'
    mail.send(msg)


# ==========================================
#  STEP 1: ENTER EMAIL
# ==========================================
@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        
        # 1. Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered. Please log in.', category='error')
            return redirect(url_for('auth.login'))
        
        # 2. Generate 6-digit OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # 3. Store in Session
        session['signup_email'] = email
        session['signup_otp'] = otp
        
        # 4. Send Email
        try:
            sender_email = os.getenv('MAIL_USERNAME')
            msg = Message('Your Verification Code - AV Postory', 
                  sender=sender_email, 
                  recipients=[email])
            
            msg.body = f'Your verification code is: {otp}\n\nDo not share this code.'
            mail.send(msg)
            
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



#Check Username Availability for Sign Up
@auth.route('/check-username-signup', methods=['POST'])
def check_username_signup():
    data = request.json
    username = data.get('username', '').strip()

    if not username:
        return jsonify({'available': False, 'message': 'Username cannot be empty.'})

    if len(username) < 3:
        return jsonify({'available': False, 'message': 'Username must be at least 3 characters.'})

    # Check database
    user = User.query.filter_by(username=username).first()

    if user:
        return jsonify({'available': False, 'message': 'Username is already taken.'})
    else:
        return jsonify({'available': True, 'message': 'Username is available!'})

# ==========================================
#  STEP 3: CREATE USERNAME & PASSWORD
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
        
        # Validations
        if len(username) < 2:
            flash('Username must be greater than 1 character.', category='error')
        
        # ✅ NEW STRICT VALIDATION: No spaces or special chars
        elif not re.match("^[a-zA-Z0-9_.]+$", username):
            flash("Username can only contain letters, numbers, dots (.), and underscores (_). No spaces.", category='error')
            
        elif password != confirm_password:
            flash('Passwords don\'t match.', category='error')
        elif len(password) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            new_user = User(email=email, username=username, 
                            password=generate_password_hash(password, method='scrypt'), 
                            is_verified=True,
                            date_created=datetime.now()) # Use Local Time
            
            db.session.add(new_user)
            db.session.commit()
            
            login_user(new_user, remember=True)
            
            session.pop('signup_email', None)
            session.pop('signup_otp', None)
            session.pop('email_verified', None)
            
            flash('Account created successfully!', category='success')
            return redirect(url_for('views.home'))

    return render_template("finish_signup.html", user=current_user)

# ==========================================
#  ROUTES
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

                # ✅ FIX: Use Local Time for Last Login (matches views.py)
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

@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
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