```markdown
# AV Postory

**A modern, clean, and delightful social blogging platform** — built for writers, developers, and thinkers who value depth over noise.



---

## ✨ About AV Postory

AV Postory is a full-featured social publishing platform where users can write rich stories, connect with others through real-time chat, follow creators, and engage in meaningful discussions — all in a beautiful, distraction-free environment.


---

## 🚀 Key Features

### Core Features
- **Rich Text Editor** with Quill.js (mentions, hashtags, link previews, code highlighting, image upload)
- **Infinite Scroll Feed** with "Continue Reading" progress
- **Real-time Chat** powered by Flask-SocketIO
- **Live Notifications** (likes, comments, follows, mentions, messages)
- **Follow System** + Follower/Following lists
- **Like, Comment, Save, Share** posts
- **Block & Report** system for safety
- **Advanced Search** with user & post suggestions

### User Experience
- Beautiful **Dark Mode** with system preference detection
- Fully responsive design (mobile-first)
- Smooth animations and modern UI/UX
- First-time user onboarding checklist
- Reading progress tracking

### Admin & Moderation
- Powerful **Admin Dashboard**
- User management, post moderation, comment control
- Report handling system

### Technical Highlights
- Secure authentication with OTP email verification
- Cloudinary image hosting + optimization
- Rate limiting & spam protection
- CSRF & XSS protection (Bleach sanitization)
- PostgreSQL ready (SQLite for development)

---

## 🛠 Tech Stack

| Layer           | Technology                                      |
|-----------------|-------------------------------------------------|
| Backend         | Flask, SQLAlchemy, Flask-Login, Flask-SocketIO |
| Database        | PostgreSQL (Production) / SQLite (Development) |
| Frontend        | Jinja2, Bootstrap 5, Vanilla JS                 |
| Rich Editor     | Quill.js + Quill Mention + Highlight.js         |
| Real-time       | Socket.IO                                       |
| Image Hosting   | Cloudinary                                      |
| Emails          | Flask-Mail + Async ThreadPoolExecutor           |
| Styling         | Custom CSS Variables + Dark Mode                |
| Migrations      | Flask-Migrate                                   |
| Rate Limiting   | Flask-Limiter                                   |

---

## 📸 Screenshots

*(Add screenshots here once ready)*

- Home Feed
- Rich Text Editor
- Real-time Chat
- Profile Page
- Notifications
- Admin Dashboard
- Mobile View

---

## 🛠 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/av-postory.git
cd av-postory
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Create a `.env` file in the root directory:

```env
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-here

# Email Configuration (Gmail recommended)
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Optional: Production Database
DATABASE_URL=postgresql://user:password@localhost/avpostory

# Public Domain (for email links)
PUBLIC_DOMAIN=https://yourdomain.com
```

### 5. Database Setup
```bash
# Initialize migrations (first time only)
flask db init

# Create migration
flask db migrate -m "Initial migration"

# Apply migrations
flask db upgrade
```

### 6. Run the Application
```bash
python app.py
```

The app will be available at `http://localhost:8001`

---

## 📌 How to Use

- **Sign Up** → Verify email via OTP
- **Create Posts** → Use rich editor with mentions and image upload
- **Engage** → Like, comment, save, follow
- **Chat** → Real-time messaging with typing indicators
- **Admin** → Access `/admin` (only for admin users)

---

## 🧩 Project Structure

```
av-postory/
├── website/
│   ├── __init__.py          # App factory
│   ├── config.py
│   ├── models.py
│   ├── views.py
│   ├── auth.py
│   ├── utils.py
│   ├── events.py            # SocketIO events
│   └── templates/           # All HTML templates
├── static/
│   ├── styles.css
│   ├── index.js
│   └── uploads/             # Local uploads (dev)
├── migrations/              # Alembic migrations
├── .env
├── app.py
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Feel free to:

1. Fork the project
2. Create a feature branch
3. Submit a Pull Request

Please follow the existing code style and comment your changes.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Anannay Varshney**  
Creator of AV Postory

- GitHub: [@AV-2668877724](https://github.com/AV-2668877724)
- Twitter/X: [@av_indian007](https://x.com/av_indian007)
- LinkedIn: [Anannay Varshney](https://www.linkedin.com/in/anannay-varshney-765a32261)

---

