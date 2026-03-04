# AV Postory 📝✨

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey.svg?style=flat-square&logo=flask&logoColor=white)
![Cloudinary](https://img.shields.io/badge/Cloudinary-Image%20Hosting-blue.svg?style=flat-square&logo=cloudinary&logoColor=white)
![Socket.IO](https://img.shields.io/badge/Socket.IO-Real%20Time-black.svg?style=flat-square&logo=socket.io&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)

**AV Postory** is a modern, feature-rich social blogging platform built with Python and Flask. It empowers users to write beautifully formatted stories, engage with a vibrant community through likes and nested comments, and connect privately via real-time WebSockets chat.

---

## 📑 Table of Contents
1. [About the Project](#-about-the-project)
2. [Core Features](#-core-features)
3. [Tech Stack](#-tech-stack)
4. [Getting Started (Installation)](#-getting-started)
5. [Environment Variables](#-environment-variables)
6. [Project Structure](#-project-structure)
7. [Screenshots](#-screenshots)
8. [Contributing](#-contributing)
9. [License](#-license)

---

## 🚀 About the Project
AV Postory was created to bridge the gap between traditional blogging and modern social media. Whether you are publishing a long-form article using our rich-text editor or having a quick 1-on-1 chat with a follower, the platform is designed to be fast, secure, and visually stunning across all devices.

---

## ✨ Core Features

### 🔐 Authentication & Security
* **Secure Access:** Sign-up, Login, and Logout functionality with robust "Remember Me" session management.
* **Data Protection:** Passwords are mathematically hashed using Werkzeug.
* **CSRF Protection:** Global Cross-Site Request Forgery (WTF) protection on all forms and API routes.
* **XSS Prevention:** HTML sanitization using Bleach prevents malicious script injections.
* **Account Deactivation:** A multi-step deactivation flow featuring an "emotional plea" retention UI and exit-reason logging.

### 👤 Profile & Community
* **Custom Profiles:** Personalize with custom bios, profile pictures, and cover photos.
* **Smart Social Links:** Add personal URLs (GitHub, Twitter, LinkedIn) that automatically render the correct brand icons.
* **Follow System:** Build an audience with real-time follower/following tracking.

### ✍️ Blogging Engine
* **Rich Text Editor:** Powered by Quill.js for creating beautifully formatted stories.
* **Cloud Images:** Attach dynamic cover photos seamlessly hosted and optimized on Cloudinary.
* **Smart Feed:** "Read More" truncation keeps the main feed clean, accompanied by time-ago timestamps and clipboard link-sharing.

### 💬 Social Engagement & Real-Time Chat
* **Interactive Posts:** Like and unlike posts and individual comments with live counters.
* **Nested Comments:** Engage in discussions with strict ownership control (only authors or admins can delete).
* **Live Private Messaging:** 1-on-1 real-time chat powered by Flask-SocketIO.
* **Advanced Chat UX:** Live online/offline status indicators, message deletion, and infinite-scroll pagination for loading historical messages.
* **Smart Notifications:** Real-time alerts for interactions that group intelligently (e.g., *"User and 5+ others liked your post"*).

### 🛡️ Super Admin Dashboard
* **Centralized Hub:** View platform statistics (users, active/deleted posts, total comments).
* **Content Moderation:** Soft-delete, permanently destroy, or restore user posts and comments.
* **User Management:** Disable/reactivate user accounts and review exit feedback.
* **Security Lock:** Master password protection required before executing any destructive actions.

### 🎨 UI/UX Enhancements
* **System-Wide Themes:** Seamless Dark Mode and Light Mode toggling.
* **Mobile-First Design:** Fully responsive layout featuring a mobile app-style bottom navigation bar.
* **Interactive Elements:** Drag-and-drop image upload zones, image lightboxes, and toast notifications.
* **Global Search:** Live AJAX dropdown search bar for finding users and content.

---

## 💻 Tech Stack

**Backend:**
* [Python 3](https://www.python.org/)
* [Flask](https://flask.palletsprojects.com/)
* [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) (ORM) & SQLite (Database)
* [Flask-SocketIO](https://flask-socketio.readthedocs.io/) (WebSockets)
* [Flask-Login](https://flask-login.readthedocs.io/) (Session Management)

**Frontend:**
* HTML5, CSS3, Vanilla JavaScript
* [Bootstrap 5.3.2](https://getbootstrap.com/)
* [Quill.js](https://quilljs.com/) (Rich Text Editor)
* FontAwesome & Bootstrap Icons

**Cloud & Integrations:**
* [Cloudinary API](https://cloudinary.com/) (Image hosting and delivery)

---

## 🛠️ Getting Started

Follow these steps to set up the project locally on your machine.

### 1. Prerequisites
* Python 3.8 or higher installed.
* A free [Cloudinary](https://cloudinary.com/) account for image uploads.

### 2. Clone the Repository
```bash
git clone [https://github.com/yourusername/av-postory.git](https://github.com/yourusername/av-postory.git)
cd av-postory