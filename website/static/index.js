/* =========================================
   GLOBAL CONFIG & HELPER FUNCTIONS
   ========================================= */
const TRUNCATE_HEIGHT = 400;

function truncatePosts() {
  document.querySelectorAll(".post-text").forEach((el) => {
    if (el.dataset.processed) return;
    const overlay = el.parentElement.querySelector(".fade-overlay");
    if (el.scrollHeight > TRUNCATE_HEIGHT) {
      if (overlay) overlay.style.display = "block";
      el.style.maxHeight = `${TRUNCATE_HEIGHT}px`;
      el.style.overflow = "hidden";
    }
    el.dataset.processed = "true";
  });
}

/* =========================================
   MAIN DOM LOAD LOGIC
   ========================================= */
document.addEventListener("DOMContentLoaded", () => {
  /* --- DARK MODE --- */
  const darkToggle = document.getElementById("darkToggle");
  const saved = localStorage.getItem("darkMode") === "true";

  if (darkToggle) {
    setDarkMode(saved);
    darkToggle.addEventListener("click", () => {
      const enabled = document.body.classList.toggle("dark-mode");
      localStorage.setItem("darkMode", enabled);
      setDarkMode(enabled);
    });
  } else {
    document.body.classList.remove("dark-mode");
  }

  /* --- AUTO TOAST SHOW --- */
  document
    .querySelectorAll("#toastContainer .toast")
    .forEach((t) => new bootstrap.Toast(t, { delay: 3000 }).show());

  /* --- INITIAL POST TRUNCATION --- */
  truncatePosts();

  /* --- READ MORE / READ LESS DELEGATION --- */
  document.addEventListener("click", function (e) {
    if (e.target && e.target.classList.contains("see-more-btn")) {
      const btn = e.target;
      const postId = btn.dataset.postId;
      const postText = document.getElementById(`post-text-${postId}`);
      const overlay = document.getElementById(`fade-overlay-${postId}`);

      if (!postText) return;

      if (btn.innerText.trim() === "Read More") {
        postText.style.maxHeight = "none";
        postText.style.overflow = "visible";
        btn.innerText = "Read Less";
        if (overlay) overlay.style.display = "none";
      } else {
        postText.style.maxHeight = `${TRUNCATE_HEIGHT}px`;
        postText.style.overflow = "hidden";
        btn.innerText = "Read More";
        if (overlay) overlay.style.display = "block";

        const rect = btn.getBoundingClientRect();
        window.scrollTo({
          top: window.scrollY + rect.top - 100,
          behavior: "smooth",
        });
      }
    }
  });

  /* --- NOTIFICATION BADGE --- */
  const notifBtn = document.getElementById("notifDropdown");
  if (notifBtn) {
    notifBtn.addEventListener("click", () => {
      const badge = document.getElementById("notifBadge");
      if (badge) {
        badge.style.display = "none";
        fetch("/api/mark-notifications-read", { method: "POST" }).catch((err) =>
          console.error("Error marking read:", err),
        );
      }
    });
  }

  /* --- TIMESTAMP REFRESH --- */
  refreshTimestamps();
  setInterval(refreshTimestamps, 60000);

  /* --- LIVE SEARCH (AUTOCOMPLETE) --- */
  const searchInput = document.getElementById("searchInput");
  const searchResults = document.getElementById("searchResults");

  if (searchInput && searchResults) {
    searchInput.addEventListener("input", async function () {
      const query = this.value.trim();

      if (query.length < 1) {
        searchResults.classList.remove("show");
        return;
      }

      try {
        const response = await fetch(`/api/search-users?q=${query}`);
        const users = await response.json();
        searchResults.innerHTML = "";

        if (users.length > 0) {
          users.forEach((user) => {
            const item = document.createElement("a");
            item.className =
              "dropdown-item d-flex align-items-center gap-2 py-2";
            item.href = `/profile/${user.username}`;

            let avatarHtml = "";
            if (user.profile_pic) {
              avatarHtml = `<img src="/static/uploads/avatars/${user.profile_pic}" class="rounded-circle border" style="width: 30px; height: 30px; object-fit: cover;">`;
            } else {
              const initial = user.username.charAt(0).toUpperCase();
              avatarHtml = `<div class="d-flex align-items-center justify-content-center bg-secondary text-white rounded-circle" style="width: 30px; height: 30px; font-size: 0.8rem; font-weight: bold;">${initial}</div>`;
            }

            item.innerHTML = `${avatarHtml} <span>${user.username}</span>`;
            searchResults.appendChild(item);
          });
          searchResults.classList.add("show");
          searchResults.style.display = "block";
        } else {
          searchResults.classList.remove("show");
          searchResults.style.display = "none";
        }
      } catch (error) {
        console.error("Search error:", error);
      }
    });

    searchInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        window.location.href = `/search-page?q=${this.value}`;
      }
    });

    document.addEventListener("click", function (e) {
      if (
        !searchInput.contains(e.target) &&
        !searchResults.contains(e.target)
      ) {
        searchResults.classList.remove("show");
        searchResults.style.display = "none";
      }
    });
  }

  /* --- GLOBAL USERNAME INPUT VALIDATION --- */
  const usernameInputs = document.querySelectorAll('input[name="username"]');
  usernameInputs.forEach((input) => {
    input.addEventListener("keypress", function (e) {
      const regex = /[a-zA-Z0-9_.]/;
      if (!regex.test(e.key)) {
        e.preventDefault();
      }
    });
  });
});

/* =========================================
   UI HELPERS (Dark Mode, Toasts, Time)
   ========================================= */
function setDarkMode(enabled) {
  const icon = document.querySelector("#darkToggle i");
  if (enabled) {
    document.body.classList.add("dark-mode");
    if (icon) icon.className = "fas fa-sun";
  } else {
    document.body.classList.remove("dark-mode");
    if (icon) icon.className = "fas fa-moon";
  }
}

function showToast(message, isError = false) {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast align-items-center ${
    isError ? "text-bg-danger" : "text-bg-success"
  } border-0`;
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
  container.appendChild(toast);

  const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
  bsToast.show();
  toast.addEventListener("hidden.bs.toast", () => toast.remove());
}

/* =========================================
   LIKE POST LOGIC
   ========================================= */
function likePost(postId, btn) {
  like(postId);
}

function like(postId) {
  const countEl = document.getElementById(`likes-count-${postId}`);
  const btn = document.getElementById(`like-button-${postId}`);
  const icon = btn ? btn.querySelector("i") || btn : null;

  if (!countEl || !btn) return;
  if (btn.dataset.loading === "true") return;
  btn.dataset.loading = "true";

  const isFar = icon.classList.contains("far");
  const current = parseInt(countEl.innerText, 10) || 0;

  if (isFar) {
    countEl.innerText = current + 1;
    icon.classList.remove("far");
    icon.classList.add("fas", "text-danger");
    btn.classList.add("like-anim");
    setTimeout(() => btn.classList.remove("like-anim"), 600);
  } else {
    countEl.innerText = Math.max(0, current - 1);
    icon.classList.remove("fas", "text-danger");
    icon.classList.add("far");
  }

  fetch(`/like-post/${postId}`, { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      countEl.innerText = data.likes;
      if (data.liked) {
        icon.classList.add("fas", "text-danger");
        icon.classList.remove("far");
      } else {
        icon.classList.add("far");
        icon.classList.remove("fas", "text-danger");
      }
    })
    .catch(() => showToast("Network error", true))
    .finally(() => (btn.dataset.loading = "false"));
}

/* =========================================
   LIKE COMMENT LOGIC
   ========================================= */
document.addEventListener("click", function (e) {
  const btn = e.target.closest(".btn-comment, .comment-btn-trigger");
  if (btn) {
    btn.classList.add("ripple-effect", "ripple-active");
    setTimeout(() => btn.classList.remove("ripple-active"), 500);
  }
});

function likeComment(commentId, btn) {
  if (btn.dataset.loading === "true") return;
  btn.dataset.loading = "true";

  const icon = btn.querySelector("i");
  const countSpan = btn.querySelector(".like-count");
  const currentCount = parseInt(countSpan.innerText, 10) || 0;
  const isLiked = icon.classList.contains("fas");

  if (isLiked) {
    icon.classList.remove("fas", "text-danger");
    icon.classList.add("far");
    countSpan.innerText = Math.max(0, currentCount - 1);
  } else {
    icon.classList.remove("far");
    icon.classList.add("fas", "text-danger");
    countSpan.innerText = currentCount + 1;
    icon.style.transform = "scale(1.3)";
    icon.style.transition = "transform 0.2s";
    setTimeout(() => (icon.style.transform = "scale(1)"), 200);
  }

  fetch(`/like-comment/${commentId}`, { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      countSpan.innerText = data.likes;
      if (data.liked) {
        icon.classList.add("fas", "text-danger");
        icon.classList.remove("far");
      } else {
        icon.classList.add("far");
        icon.classList.remove("fas", "text-danger");
      }
    })
    .catch(() => console.error("Error liking comment"))
    .finally(() => (btn.dataset.loading = "false"));
}

/* =========================================
   TIME AGO FORMATTER
   ========================================= */
function timeAgoFromISO(isoString) {
  const now = new Date();
  const then = new Date(isoString);
  const diffSeconds = Math.floor((now - then) / 1000);

  if (diffSeconds < 60) return "just now";
  const minutes = Math.floor(diffSeconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} day${days > 1 ? "s" : ""} ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 4) return `${weeks} week${weeks > 1 ? "s" : ""} ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} month${months > 1 ? "s" : ""} ago`;
  const years = Math.floor(days / 365);
  return `${years} year${years > 1 ? "s" : ""} ago`;
}

function refreshTimestamps() {
  document.querySelectorAll("[data-timestamp]").forEach((el) => {
    const ts = el.getAttribute("data-timestamp");
    if (ts) el.textContent = timeAgoFromISO(ts);
  });
}

/* =========================================
   ADMIN DASHBOARD HELPERS
   ========================================= */
window.handleEnterSearch = function (event, sectionId, value) {
  const section = document.getElementById(sectionId);
  if (!section) return;

  if (event.key === "Enter") {
    event.preventDefault();
    if (!section.classList.contains("show")) {
      new bootstrap.Collapse(section, { show: true });
    }
    applyAdminFilter(sectionId, value);
  }

  if (event.key === "Escape") {
    event.preventDefault();
    event.target.value = "";
    resetAdminFilter(sectionId);
  }
};

function applyAdminFilter(sectionId, query) {
  query = query.trim().toLowerCase();
  const section = document.getElementById(sectionId);
  const info = document.getElementById(sectionId + "-info");

  if (!query) {
    resetAdminFilter(sectionId);
    return;
  }

  let count = 0;
  section.querySelectorAll(".admin-row").forEach((row) => {
    const item = row.querySelector(".admin-item");
    let match = false;
    if (item.dataset.username) {
      match = item.dataset.username.toLowerCase() === query;
    } else {
      match = item.dataset.search.toLowerCase().includes(query);
    }
    row.classList.toggle("d-none", !match);
    if (match) count++;
  });

  if (info) {
    info.textContent = count
      ? `${count} result${count > 1 ? "s" : ""} found`
      : "No results found";
  }
}

function resetAdminFilter(sectionId) {
  const section = document.getElementById(sectionId);
  const info = document.getElementById(sectionId + "-info");
  section.querySelectorAll(".admin-row").forEach((row) => {
    row.classList.remove("d-none");
  });
  if (info) info.textContent = "";
}

/* =========================================
   USERNAME AVAILABILITY (SIGNUP ONLY)
   ========================================= */

function checkSignupUsername() {
  const usernameInput = document.getElementById("signupUsername");
  const statusDiv = document.getElementById("signupUsernameStatus");
  const submitBtn = document.getElementById("signupSubmitBtn"); // The Create Account button
  const checkBtn = document.getElementById("checkBtn");

  const username = usernameInput.value.trim();

  // 1. Basic Validation
  if (username.length < 3) {
    statusDiv.innerHTML = '<span class="text-danger">Too short (min 3 chars).</span>';
    submitBtn.disabled = true;
    return;
  }

  // 2. Show Loading State
  checkBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  checkBtn.disabled = true;

  // 3. Call the Correct Backend API
  fetch("/check-username-signup", {  // ✅ Points to auth.py route
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: username }),
  })
    .then((res) => res.json())
    .then((data) => {
      checkBtn.innerHTML = "Check";
      checkBtn.disabled = false;

      if (data.available) {
        // Success: Unlock the Create Account button
        statusDiv.innerHTML = `<span class="text-success"><i class="fas fa-check-circle"></i> ${data.message}</span>`;
        submitBtn.disabled = false; 
        usernameInput.classList.remove("is-invalid");
        usernameInput.classList.add("is-valid");
      } else {
        // Failure: Keep it locked
        statusDiv.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle"></i> ${data.message}</span>`;
        submitBtn.disabled = true;
        usernameInput.classList.add("is-invalid");
      }
    })
    .catch(() => {
      checkBtn.innerHTML = "Check";
      checkBtn.disabled = false;
      statusDiv.innerHTML = '<span class="text-warning">Server error. Try again.</span>';
    });
}

function resetSignupCheck() {
  const submitBtn = document.getElementById("signupSubmitBtn");
  const statusDiv = document.getElementById("signupUsernameStatus");
  const usernameInput = document.getElementById("signupUsername");

  // Lock the button immediately if they type anything new
  if (submitBtn) submitBtn.disabled = true;
  if (statusDiv) statusDiv.innerHTML = '<span class="text-muted small">Please check availability.</span>';
  if (usernameInput) usernameInput.classList.remove("is-valid", "is-invalid");
}
// 3. Profile Edit Logic
let allowUsernameSubmit = false;
function checkUsername() {
  const input = document.getElementById("newUsername");
  const status = document.getElementById("usernameStatus");
  const submitBtn = document.getElementById("submitUsernameBtn");
  const username = input.value.trim();

  if (!username) {
    status.textContent = "Please enter a username";
    status.className = "text-danger";
    submitBtn.disabled = true;
    allowUsernameSubmit = false;
    return;
  }

  fetch("/check-username", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  })
    .then((res) => res.json())
    .then((data) => {
      status.textContent = data.message;
      if (data.available) {
        status.className = "text-success";
        submitBtn.disabled = false;
        allowUsernameSubmit = true;
        document.getElementById("finalUsername").value = username;
      } else {
        status.className = "text-danger";
        submitBtn.disabled = true;
        allowUsernameSubmit = false;
      }
    });
}

/* =========================================
   PRELOADER SYSTEM
   ========================================= */
const loader = document.getElementById("preloader");
let safetyTimer = null;

function hideLoader() {
  if (loader) {
    loader.classList.add("loader-hidden");
    if (safetyTimer) clearTimeout(safetyTimer);
  }
}

function showLoader() {
  if (loader) {
    loader.classList.remove("loader-hidden");
    if (safetyTimer) clearTimeout(safetyTimer);
    safetyTimer = setTimeout(() => {
      if (!loader.classList.contains("loader-hidden")) {
        console.warn("Loading took too long. Redirecting home...");
        window.location.href = "/";
      }
    }, 8000);
  }
}

window.addEventListener("load", function () {
  setTimeout(hideLoader, 300);
});

window.addEventListener("pageshow", function (event) {
  if (
    event.persisted ||
    (window.performance && window.performance.navigation.type === 2)
  ) {
    hideLoader();
  }
});

document.addEventListener("click", function (e) {
  const target = e.target.closest("a");
  if (target) {
    const href = target.getAttribute("href");
    const targetAttr = target.getAttribute("target");
    const toggleAttr = target.getAttribute("data-bs-toggle");
    const dismissAttr = target.getAttribute("data-bs-dismiss");
    const actionAttr = target.getAttribute("onclick");

    if (
      href &&
      !href.startsWith("#") &&
      !href.startsWith("javascript") &&
      targetAttr !== "_blank" &&
      !toggleAttr &&
      !dismissAttr &&
      !actionAttr
    ) {
      showLoader();
    }
  }
});

document.addEventListener("submit", function (e) {
  if (e.defaultPrevented) return;

  const form = e.target;
  if (form.id === "chatForm") return;

  if (form.checkValidity()) {
    showLoader();
  }
});

/* =========================================
   INFINITE SCROLL
   ========================================= */
document.addEventListener("DOMContentLoaded", function () {
  const sentinel = document.getElementById("sentinel");
  const container = document.getElementById("posts-container");
  const endMessage = document.getElementById("end-message");
  const spinner = document.getElementById("scroll-spinner");

  if (sentinel) {
    let isLoading = false;
    const observer = new IntersectionObserver(
      (entries) => {
        const hasNext = sentinel.getAttribute("data-has-next") === "true";
        if (entries[0].isIntersecting && hasNext && !isLoading) {
          loadMorePosts();
        } else if (!hasNext && endMessage) {
          endMessage.classList.remove("d-none");
        }
      },
      { rootMargin: "200px" },
    );

    observer.observe(sentinel);

    async function loadMorePosts() {
      if (isLoading) return;
      isLoading = true;
      spinner.style.display = "inline-block";

      let page = parseInt(sentinel.getAttribute("data-page"));
      const baseUrl = sentinel.getAttribute("data-url");
      const nextPage = page + 1;

      try {
        const response = await fetch(`${baseUrl}?page=${nextPage}&ajax=1`);
        if (!response.ok) throw new Error("Failed to load");
        const html = await response.text();

        if (html.trim().length === 0) {
          sentinel.setAttribute("data-has-next", "false");
          if (endMessage) endMessage.classList.remove("d-none");
          spinner.style.display = "none";
          return;
        }

        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = html;
        while (tempDiv.firstChild) {
          container.appendChild(tempDiv.firstChild);
        }
        truncatePosts();
        sentinel.setAttribute("data-page", nextPage);
      } catch (error) {
        console.error("Scroll Error:", error);
      } finally {
        isLoading = false;
        spinner.style.display = "none";
      }
    }
  }
});

/* =========================================
   REAL-TIME CHAT & PRESENCE (SOCKET.IO)
   ========================================= */
document.addEventListener("DOMContentLoaded", function () {
  const chatForm = document.getElementById("chatForm");
  const chatBox = document.getElementById("chat-box");

  if (chatForm && chatBox) {
    const socket = io();
    const recipientId = chatForm.dataset.recipient;
    chatBox.scrollTop = chatBox.scrollHeight;

    socket.on("receive_message", function (msg) {
      if (msg.sender_id == recipientId || msg.sender_id == "{{ user.id }}") {
        appendMessageToChat(msg);
        chatBox.scrollTop = chatBox.scrollHeight;
      }
    });

    socket.on("user_status_change", function (data) {
      if (data.user_id == recipientId) {
        const statusContainer = document.getElementById(
          `status-container-${recipientId}`,
        );
        const statusText = document.getElementById(
          `status-text-${recipientId}`,
        );
        const icon = statusContainer
          ? statusContainer.querySelector("i")
          : null;

        if (statusContainer && statusText && icon) {
          if (data.status === "online") {
            icon.className = "fas fa-circle text-success";
            statusText.innerText = "Online";
          } else {
            icon.className = "fas fa-circle text-secondary";
            statusText.innerText =
              "Last seen " + (data.last_seen || "recently");
          }
        }
      }
    });

    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const messageInput = document.getElementById("messageInput");
      const text = messageInput.value.trim();
      if (!text) return;
      socket.emit("send_message", { recipient_id: recipientId, text: text });
      messageInput.value = "";
    });

    function appendMessageToChat(msg) {
      if (document.querySelector(`.message-row[data-msg-id="${msg.id}"]`)) {
        return;
      }

      const isMe = msg.sender_id != recipientId;
      let html = "";

      if (isMe) {
        html = `
            <div class="d-flex w-100 mb-3 align-items-end message-row justify-content-end" data-msg-id="${msg.id}">
                <div class="d-flex align-items-end justify-content-end w-100">
                    <button class="btn btn-sm btn-link text-muted p-0 me-2 opacity-50 hover-opacity-100 delete-btn" 
                            onclick="deleteMessage('${msg.id}', this)" title="Delete for me">
                        <i class="fas fa-trash-alt" style="font-size: 0.8rem;"></i>
                    </button>
                    <div class="bg-primary text-white rounded-3 px-3 py-2 shadow-sm" style="max-width: 75%;">
                        ${msg.text}
                        <div class="text-white-50 text-end" style="font-size: 0.65rem;">${msg.time}</div>
                    </div>
                </div>
            </div>`;
      } else {
        html = `
            <div class="d-flex w-100 mb-3 align-items-end message-row justify-content-start" data-msg-id="${msg.id}">
                <div class="d-flex align-items-end justify-content-start w-100">
                    <div class="bg-white text-dark border rounded-3 px-3 py-2 shadow-sm" style="max-width: 75%;">
                        ${msg.text}
                        <div class="text-muted text-end" style="font-size: 0.65rem;">${msg.time}</div>
                    </div>
                    <button class="btn btn-sm btn-link text-muted p-0 ms-2 opacity-50 hover-opacity-100 delete-btn" 
                            onclick="deleteMessage('${msg.id}', this)" title="Delete for me">
                        <i class="fas fa-trash-alt" style="font-size: 0.8rem;"></i>
                    </button>
                </div>
            </div>`;
      }
      chatBox.insertAdjacentHTML("beforeend", html);
    }
  }
});

/* =========================================
   DELETE MESSAGE (API CALL)
   ========================================= */
function deleteMessage(msgId, btnElement) {
  if (!confirm("Delete this message for me?")) return;

  fetch(`/api/delete-message/${msgId}`, { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        const messageRow =
          btnElement.closest(".message-row") ||
          btnElement.closest(".d-flex.w-100");
        if (messageRow) {
          messageRow.style.transition = "opacity 0.3s";
          messageRow.style.opacity = "0";
          setTimeout(() => messageRow.remove(), 300);
        }
      } else {
        alert("Error deleting message");
      }
    })
    .catch((err) => console.error(err));
}

/* =========================================
   PROFILE PAGE (Follow, Avatar, Socials)
   ========================================= */
function previewImage(input, imgId) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function (e) {
      const img = document.getElementById(imgId);
      if (img) {
        img.src = e.target.result;
        img.classList.remove("d-none");
      }
    };
    reader.readAsDataURL(input.files[0]);
  }
}

function viewFullSize(src) {
  const modal = new bootstrap.Modal(document.getElementById("imageViewModal"));
  const img = document.getElementById("fullSizeImage");
  img.src = src;
  modal.show();
}

function removeSocialLink(url) {
  if (!confirm("Remove this link?")) return;

  fetch("/profile/remove-social", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: url }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) location.reload();
      else alert(data.message);
    })
    .catch((err) => console.error("Error:", err));
}

function toggleFollow(userId, btn) {
  const isFollowing = btn.innerText.trim() === "Following";
  const url = isFollowing ? `/unfollow/${userId}` : `/follow/${userId}`;

  fetch(url, { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        if (data.action === "followed") {
          btn.innerText = "Following";
          btn.classList.remove("btn-primary");
          btn.classList.add("btn-outline-secondary");
        } else {
          btn.innerText = "Follow";
          btn.classList.remove("btn-outline-secondary");
          btn.classList.add("btn-primary");
        }
      } else {
        alert(data.message || "Error processing request");
      }
    })
    .catch((err) => console.error("Error:", err));
}

/* =========================================
   FORCE RELOAD ON PAGE NAVIGATION
   ========================================= */
window.addEventListener("pageshow", function (event) {
  var historyTraversal =
    event.persisted ||
    (typeof window.performance != "undefined" &&
      window.performance.navigation.type === 2);
  if (historyTraversal) {
    window.location.reload();
  }
});