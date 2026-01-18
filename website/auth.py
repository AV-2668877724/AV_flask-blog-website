from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, mail
from flask_login import login_user, login_required, logout_user, current_user
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

auth = Blueprint('auth', __name__)

# Setup Token Serializer
s = URLSafeTimedSerializer('CCAV@129') 

# ==========================================
#  HELPER: SEND EMAILS
# ==========================================
def send_verification_email(user_email):
    token = s.dumps(user_email, salt='email-confirm')
    link = url_for('auth.confirm_email', token=token, _external=True)
    
    # ✅ Using your real Gmail to prevent errors
    msg = Message('Confirm Your Email - AV Postory', 
                  sender='varshneyanurag888@gmail.com', 
                  recipients=[user_email])
    
    msg.body = f'Your link is: {link}\n\nThis link expires in 1 hour.'
    mail.send(msg)

def send_reset_email(user_email):
    token = s.dumps(user_email, salt='password-reset')
    link = url_for('auth.reset_token', token=token, _external=True)
    
    # ✅ Using your real Gmail to prevent errors
    msg = Message('Password Reset Request', 
                  sender='varshneyanurag888@gmail.com', 
                  recipients=[user_email])
    
    msg.body = f'To reset your password, click the following link: {link}'
    mail.send(msg)

# ==========================================
#  ROUTES
# ==========================================

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(username) < 2:
            flash('Username must be greater than 1 character.', category='error')
        elif password != confirm_password:
            flash('Passwords don\'t match.', category='error')
        elif len(password) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            # Create User (Unverified initially)
            new_user = User(email=email, username=username, 
                            password=generate_password_hash(password, method='scrypt'), 
                            is_verified=False)
            
            db.session.add(new_user)
            db.session.commit()
            
            try:
                send_verification_email(email)
                flash('Account created! Please check your email to verify.', category='success')
                return redirect(url_for('auth.login'))
            except Exception as e:
                # If email fails, you might want to log this error
                print(e)
                flash('Account created, but verification email failed to send.', category='error')
                return redirect(url_for('auth.login'))

    return render_template("sign_up.html", user=current_user)

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
                # Check verification status
                if not user.is_verified:
                    flash('Please verify your email first.', category='error')
                    return render_template("login.html", user=current_user)

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