# 🚀 AV Postory

**The Next-Generation Social Publishing & Connection Ecosystem**

AV Postory is an advanced, distraction-free social publishing platform designed for clarity, deep connection, and creator monetization. Built with a robust Python Flask architecture and real-time WebSockets, it bridges the gap between highly scalable technical infrastructure and beautifully simple personal storytelling. It is not just a blogging website; it is a premium canvas for your intellectual and financial journey.

---

## 📑 Table of Contents

1. [About The Project](https://www.google.com/search?q=%23about-the-project)
2. [Key Features](https://www.google.com/search?q=%23key-features)
3. [Technology Stack](https://www.google.com/search?q=%23technology-stack)
4. [System Architecture & Folder Structure](https://www.google.com/search?q=%23system-architecture--folder-structure)
5. [Local Setup & Installation](https://www.google.com/search?q=%23local-setup--installation)
6. [Environment Variables (.env)](https://www.google.com/search?q=%23environment-variables-env)
7. [Utility Scripts & Database Management](https://www.google.com/search?q=%23utility-scripts--database-management)
8. [Enterprise Security & Privacy](https://www.google.com/search?q=%23enterprise-security--privacy)
9. [Future Roadmap](https://www.google.com/search?q=%23future-roadmap)
10. [Author & License](https://www.google.com/search?q=%23author--license)

---

## 📖 About The Project

In a world of fleeting tweets and algorithmic noise, AV Postory was built to restore **Depth and Usability** to the internet. What started as a personal coding challenge has evolved into a mission to build the most user-friendly ecosystem on the web.

Whether you are a writer, developer, or thinker, AV Postory provides an aesthetic, dark-mode optimized environment to share your stories, code snippets, and ideas. Beyond publishing, it features a native, real-time chat infrastructure allowing creators to connect instantly with their audience, all backed by enterprise-grade security and granular user activity tracking.

---

## ✨ Key Features

AV Postory is packed with modern, premium features designed for both performance and user experience.

* **Rich Story Editor:** A highly responsive, secure WYSIWYG editor (powered by Quill.js) allowing users to format thoughts with dynamic headings, embedded images, formatted code blocks, and smart links effortlessly.
* **Real-Time WebSockets Chat:** Built on `Flask-SocketIO`, the platform features a live, full-screen messaging system. Conversations happen in true real-time without page reloads, complete with read receipts (blue ticks) and live typing indicators.
* **Smart Native Mail Routing:** A custom JavaScript routing engine that detects the user's operating system and seamlessly triggers native mobile apps (Gmail/Zoho Mail) or gracefully opens secure web tabs for desktop users when contacting support.
* **Premium UI/UX & Skeleton Loaders:** Incorporates state-of-the-art "Skeleton Loading" states to ensure a smooth, premium feel while content is fetched from the server.
* **Dynamic Dark Mode:** A user-friendly, system-adaptive toggle that instantly switches the entire platform's theme to protect eyes and save battery life, utilizing CSS variables for seamless transitions.
* **"Blue Tick" Verification System:** An integrated monetization and trust system. Users can process secure payments via UPI QR codes to claim an authentic Blue Tick, granting top-tier feed ranking and VIP support.
* **Cloudinary Edge CDN:** All media and avatar uploads are securely processed, optimized, and delivered globally via Cloudinary's high-speed Content Delivery Network.
* **Live Notifications:** Instant, asynchronous alerts for new likes, comments, follows, and direct messages.

---

## 🛠️ Technology Stack

We utilize a scalable, modern tech stack to guarantee rapid speeds, secure connections, and total reliability.

### Backend

* **Python 3.x:** Core application logic.
* **Flask:** Lightweight, highly customizable web framework.
* **Flask-SocketIO:** For bi-directional, real-time event-driven communication.
* **SQLAlchemy (ORM):** Relational database management.
* **Flask-Mail & Zoho Mail API:** Secure, asynchronous email routing.

### Frontend

* **Vanilla JavaScript (ES6+):** Lightweight DOM manipulation and smart client-side routing.
* **Bootstrap 5:** For highly responsive, mobile-first flexbox layouts.
* **CSS3:** Custom properties for dynamic theming (Light/Dark Mode).
* **FontAwesome:** Scalable vector iconography.

### Security & Utilities

* **Bleach:** Rigorous HTML sanitization to prevent XSS attacks.
* **Flask-WTF (CSRFProtect):** Cross-Site Request Forgery token verification.
* **Flask-Limiter:** Intelligent rate-limiting to prevent DDoS and brute-force attacks.
* **Werkzeug Security:** Industry-standard password hashing (scrypt).

---

## 📂 System Architecture & Folder Structure

The project is structured using the Flask Application Factory pattern, ensuring clear separation of concerns, easy scalability, and clean modularity.

```text
AV_Postory/
│
├── .env                     # Environment variables (Ignored by Git)
├── .gitignore               # Git rules
├── app.py                   # Application Entry Point & SocketIO initialization
│
├── 🔧 UTILITY SCRIPTS
│   ├── reset_badges.py      # Force-resets notification counts
│   ├── update_read_db.py    # Adds 'is_read' message tracking
│   ├── update_status_db.py  # Adds 'is_online' & 'last_seen' tracking
│   └── update_bluetick_db.py# Schema migration for premium verification
│
├── instance/
│   └── database.db          # Local SQLite Database 
│
├── user_logs/               # Auto-generated granular activity logs
│   └── [username]_log.txt   
│
└── website/                 # Core Application Package
    ├── __init__.py          # App factory, DB init, & fail-fast secure configs
    ├── config.py            # Development/Production environment splits
    ├── auth.py              # Authentication routing (Login, OTP, Signup)
    ├── events.py            # Socket.IO Event Handlers (Chat, Status)
    ├── models.py            # Database Schemas (User, Post, Chat, Block, etc.)
    ├── utils.py             # Helper logic (Cloudinary, Bleach sanitization)
    ├── views.py             # Main application endpoints
    ├── user_logger.py       # Custom physical file logging system
    │
    ├── static/              # Public Assets
    │   ├── styles.css       # Premium CSS Variables & Animations
    │   ├── index.js         # Global JS, Skeleton UI, Smart Mail Router
    │   ├── images/          # Platform logos & Verification QR codes
    │   └── uploads/         # Local fallback media storage
    │
    └── templates/           # Jinja2 HTML Views
        ├── base.html        # Master layout, Global Nav, Dark Mode logic
        ├── base_chat.html   # Dedicated full-screen layout wrapper for chat
        ├── home.html        # Main feed
        ├── _posts.html      # Modular post card component
        ├── profile.html     # User stats, settings, & links
        ├── chat.html        # Real-time WebSocket interface
        ├── get_verified.html# Premium pricing & checkout flows
        ├── admin_logs.html  # Super-admin security monitoring panel
        └── ...              # (Various authentication and utility views)

```

---

## 💻 Local Setup & Installation

Follow these steps to get a local development environment up and running securely.

### 1. Prerequisites

Ensure you have the following installed on your machine:

* Python 3.8 or higher
* Git
* pip (Python package manager)

### 2. Clone the Repository

```bash
git clone https://github.com/YourUsername/AV_Postory.git
cd AV_Postory

```

### 3. Create a Virtual Environment

It is highly recommended to isolate project dependencies using a virtual environment.

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate

```

### 4. Install Dependencies

```bash
pip install -r requirements.txt

```

*(Note: If you do not have a requirements.txt yet, run `pip freeze > requirements.txt` on your working machine and commit it!)*

---

## 🔐 Environment Variables (.env)

AV Postory utilizes a fail-fast configuration system. **The app will not boot if the `.env` file is missing or improperly configured.** Create a `.env` file in the root directory (`AV_Postory/.env`) and add the following keys. **Never commit this file to version control.**

```env
# Server Configuration
FLASK_ENV=development
FLASK_DEBUG=True

# Security
SECRET_KEY=your_highly_secure_random_string

# Database
# DATABASE_URL=postgresql://user:pass@localhost/dbname (Optional for Production)

# Admin & Support Routing
ADMIN_PASSWORD=your_super_admin_dashboard_password
SUPPORT_EMAIL=your_support_email@gmail.com
ADMIN_EMAIL=your_personal_admin@zohomail.in

# Zoho Mail SMTP Configuration
MAIL_SERVER=smtp.zoho.in
MAIL_PORT=465
MAIL_USE_TLS=False
MAIL_USE_SSL=True
MAIL_USERNAME=your_zoho_email@zohomail.in
MAIL_PASSWORD=your_zoho_app_password

# Cloudinary Edge CDN (Media Uploads)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# External Routing
PUBLIC_DOMAIN=http://127.0.0.1:8001

```

---

## ⚙️ Running the Application

Once your `.env` is configured, you can initialize the database and boot the server.

```bash
python app.py

```

The server will start using Eventlet/Gevent (via SocketIO) and will be accessible at `http://localhost:8001`.

### Utility Scripts & Database Management

Because AV Postory uses SQLite in development, schema changes require manual migration scripts (included in the root folder). Run these from the terminal if you are pulling recent updates:

* `python update_bluetick_db.py` - Injects the `blue_tick` verification boolean into the User table.
* `python update_status_db.py` - Injects `is_online` and `last_seen` logic for chat status.
* `python reset_badges.py` - A utility to force-clear ghost notifications.

---

## 🛡️ Enterprise Security & Privacy

Privacy and security are core features of AV Postory, not afterthoughts.

* **Sanitization:** All user inputs, especially rich text from the editor, are aggressively sanitized using the `Bleach` library. Only specific, safe HTML tags are allowed, neutralizing Cross-Site Scripting (XSS) threats.
* **Request Forgery Protection:** Every POST request, including API endpoints and UI forms, requires a valid CSRF token.
* **Granular Activity Logging:** The custom `user_logger.py` module tracks specific platform actions (logins, password resets, profile updates) and saves them into physical `[username]_log.txt` files. This allows Super Admins to monitor abuse, trace bugs, and secure the platform.
* **Strict Route Protection:** User authentication is enforced globally using `@login_required`, and specific socket namespaces validate block-lists before emitting private messages.

---

## 🗺️ Future Roadmap

AV Postory is aggressively developing new features to make the platform financially beneficial for creators:

1. **The Affiliate Program:** A system allowing verified creators to generate referral links and earn direct commissions for onboarding new verified users.
2. **Native Product Advertising:** An integrated dashboard allowing creators to promote their own newsletters, courses, or digital products seamlessly within the feed.
3. **Self-Publishing Suite:** Advanced tools allowing writers to compile their top posts into structured, professional digital formats.

---

## 👨‍💻 Author

**Designed & Developed by Anannay Varshney** * **GitHub:** [AV-2668877724](https://github.com/AV-2668877724)

* **LinkedIn:** [Anannay Varshney](https://www.linkedin.com/in/anannay-varshney-765a32261)
* **X / Twitter:** [@av_indian007](https://x.com/av_indian007)

**Copyright © 2026 AV Postory. All Rights Reserved.**