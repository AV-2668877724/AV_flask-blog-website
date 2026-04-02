import os
import re
import requests
from bs4 import BeautifulSoup
import bleach
import cloudinary
import cloudinary.uploader
from datetime import datetime
from flask_login import current_user
from sqlalchemy import func
from . import db
from .models import User, Notification, Follow, SavedPost, Block

# =================================================
# CONSTANTS
# =================================================

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

QUILL_ALLOWED_TAGS = [
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'a', 
    'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
    'blockquote', 'span', 'pre', 'div', 'img' 
]

QUILL_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'target', 'rel', 'class', 'style'],
    'img': ['src', 'class', 'style'],
    'div': ['class', 'style'],
    'p': ['class', 'style'],
    'h6': ['class', 'style'],
    '*': ['class', 'style'] 
}

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

# =================================================
# MODERATION & SAFETY HELPERS
# =================================================

def get_block_lists(user_id):
    if not user_id: return [], []
    blockers = [b[0] for b in db.session.query(Block.blocker_id).filter_by(blocked_id=user_id).all()]
    blocked_by_me = [b[0] for b in db.session.query(Block.blocked_id).filter_by(blocker_id=user_id).all()]
    return blockers, blocked_by_me

# =================================================
# TEXT & LINK PROCESSING HELPERS
# =================================================

def sanitize_html(html_content):
    if not html_content:
        return html_content
    return bleach.clean(
        html_content,
        tags=QUILL_ALLOWED_TAGS,
        attributes=QUILL_ALLOWED_ATTRIBUTES,
        strip=True 
    )

def generate_link_preview(url):
    try:
        if "localhost" in url or "127.0.0.1" in url or not url.startswith("http"):
            return ""
            
        if "youtube.com" in url or "youtu.be" in url:
            oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
            response = requests.get(oembed_url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                t = data.get("title", "YouTube Video")
                i = data.get("thumbnail_url", "")
                author = data.get("author_name", "")
                
                return f"""
                <div class="og-link-preview-wrapper mt-3 mb-2">
                    <div class="card shadow-sm" style="border-radius: 12px; overflow: hidden; max-width: 500px; border: 1px solid var(--border-color); background-color: var(--bg-card);">
                        <a href="{url}" target="_blank" class="text-decoration-none" style="color: inherit;">
                            <div class="position-relative" style="height: 200px; overflow: hidden; background-color: #000;">
                                <img src="{i}" style="width: 100%; height: 100%; object-fit: cover; opacity: 0.85;">
                                <div class="position-absolute top-50 start-50 translate-middle">
                                    <i class="fab fa-youtube text-danger" style="font-size: 3.5rem; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.5)); background: white; border-radius: 30px; line-height: 1;"></i>
                                </div>
                            </div>
                            <div class="p-3" style="background-color: var(--bg-card);">
                                <h6 class="fw-bold mb-1 text-truncate" style="color: var(--text-main); font-size: 0.95rem;">{t}</h6>
                                <p class="small text-muted mb-0"><i class="fas fa-video me-1"></i> {author}</p>
                            </div>
                        </a>
                    </div>
                </div>"""

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=2.5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title = soup.find("meta", property="og:title")
            description = soup.find("meta", property="og:description")
            image = soup.find("meta", property="og:image")
            
            t = title["content"] if title and title.get("content") else soup.title.string if soup.title else ""
            d = description["content"] if description and description.get("content") else ""
            i = image["content"] if image and image.get("content") else ""
            
            if t and i:
                return f"""
                <div class="og-link-preview-wrapper mt-3 mb-2">
                    <div class="card shadow-sm" style="border-radius: 12px; overflow: hidden; max-width: 500px; border: 1px solid var(--border-color); background-color: var(--bg-card);">
                        <a href="{url}" target="_blank" class="text-decoration-none" style="color: inherit;">
                            <div style="height: 200px; overflow: hidden; background-color: #f8f9fa;">
                                <img src="{i}" style="width: 100%; height: 100%; object-fit: cover;">
                            </div>
                            <div class="p-3" style="background-color: var(--bg-card);">
                                <h6 class="fw-bold mb-1 text-truncate" style="color: var(--text-main); font-size: 0.95rem;">{t}</h6>
                                <p class="small text-muted mb-0" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">{d}</p>
                                <div class="small mt-2" style="color: var(--primary); font-weight: 600;"><i class="fas fa-external-link-alt me-1"></i>Visit link</div>
                            </div>
                        </a>
                    </div>
                </div>"""
    except Exception as e:
        print(f"Link Preview Error for {url}: {e}")
        pass
    return ""

def process_text_links(text):
    if not text:
        return text
    
    text = re.sub(r'<div class="og-link-preview-wrapper">.*?', '', text, flags=re.DOTALL)
    
    text = re.sub(r'<a[^>]*href="/search-page\?q=[^>]*>([^<]+)</a>', r'\1', text)
    text = re.sub(r'<a[^>]*href="/profile/[^>]*>([^<]+)</a>', r'\1', text)
    
    first_url = None
    anchor_match = re.search(r'<a[^>]*href="(https?://[^"]+)"', text)
    if anchor_match:
        first_url = anchor_match.group(1)
    else:
        raw_match = re.search(r'(https?://[^\s<]+)', text)
        if raw_match:
            first_url = raw_match.group(1)
            text = re.sub(r'(?<!href=")(https?://[^\s<]+)', r'<a href="\1" target="_blank" class="text-primary text-decoration-none">\1</a>', text)

    text = re.sub(r'(?<![\w&])#([a-zA-Z0-9_]+)', r'<a href="/search-page?q=\1" class="text-primary text-decoration-none fw-bold">#\1</a>', text)
    
    def replace_mention(match):
        uname = match.group(1)
        u = User.query.filter(func.lower(User.username) == uname.lower()).first()
        if u:
            return f'<a href="/profile/{u.username}" class="text-primary text-decoration-none fw-bold">@{u.username}</a>'
        return match.group(0) 
    
    text = re.sub(r'(?<![\w&])@([a-zA-Z0-9_.]+)', replace_mention, text)
    
    if first_url:
        preview_html = generate_link_preview(first_url)
        if preview_html:
            text += preview_html

    return text

def detect_platform(url: str) -> str:
    for platform, pattern in SOCIAL_PATTERNS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "link"

# =================================================
# NOTIFICATIONS & SOCIAL
# =================================================

def notify_mentions(text, post_id, current_user_id):
    if not text:
        return
    mentioned_usernames = set(re.findall(r'(?<![\w&])@([a-zA-Z0-9_.]+)', text))
    
    for uname in mentioned_usernames:
        mentioned_user = User.query.filter(func.lower(User.username) == uname.lower()).first()
        if mentioned_user and mentioned_user.id != current_user_id:
            create_notification(current_user_id, mentioned_user.id, 'mention', post_id)

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
            date_created=datetime.utcnow() 
        )
        db.session.add(notif)
        db.session.commit()

def enrich_posts(posts, all_blocked_ids=None):
    following_ids = set()
    saved_post_ids = set() 
    if all_blocked_ids is None:
        all_blocked_ids = []
    
    if current_user.is_authenticated:
        following_ids = {f.following_id for f in Follow.query.filter_by(follower_id=current_user.id).all()}
        saved_post_ids = {s.post_id for s in SavedPost.query.filter_by(user_id=current_user.id).all()} 

    for post in posts:
        post.likes_count = len(post.likes)
        post.saves_count = len(post.saved_by) 
        
        active_comments = [c for c in post.comments if not c.is_deleted and c.author not in all_blocked_ids]
        post.active_comments_count = len(active_comments)
        
        post.liked = False
        post.user_is_followed = False 
        post.saved = False 
        
        if current_user.is_authenticated:
            post.liked = any(l.author == current_user.id for l in post.likes)
            post.user_is_followed = post.author in following_ids
            post.saved = post.id in saved_post_ids 
        
        for comment in active_comments:
            comment.likes_count = len(comment.likes)
            comment.liked = False
            if current_user.is_authenticated:
                comment.liked = any(l.author == current_user.id for l in comment.likes)
        
        post.comments = active_comments
        
    return posts

# =================================================
# FILE & MEDIA UPLOADS
# =================================================

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_to_cloudinary(file, folder_name, width=None, height=None):
    cloudinary.config(
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key = os.getenv('CLOUDINARY_API_KEY'),
        api_secret = os.getenv('CLOUDINARY_API_SECRET'),
        secure = True
    )
    
    try:
        transformations = {"fetch_format": "auto", "quality": "auto"}
        if width and height:
            transformations["width"] = width
            transformations["height"] = height
            transformations["crop"] = "fill"
        elif width:
            transformations["width"] = width
            transformations["crop"] = "scale"
            
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"av_postory/{folder_name}",
            transformation=transformations
        )
        return upload_result.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None

def delete_from_cloudinary(image_url):
    if not image_url or 'res.cloudinary.com' not in image_url:
        return
    
    cloudinary.config(
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key = os.getenv('CLOUDINARY_API_KEY'),
        api_secret = os.getenv('CLOUDINARY_API_SECRET'),
        secure = True
    )
    
    try:
        path = image_url.split('/upload/')[1]
        if path.startswith('v') and '/' in path:
            version_str = path.split('/')[0]
            if version_str[1:].isdigit():
                path = path.split('/', 1)[1]
        
        public_id = path.rsplit('.', 1)[0]
        cloudinary.uploader.destroy(public_id)
        
    except Exception as e:
        print(f"❌ Cloudinary deletion error: {e}")