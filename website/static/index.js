/* =========================================
   GLOBAL CONFIG & HELPER FUNCTIONS
   ========================================= */
const TRUNCATE_HEIGHT = 320;

function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute("content") : "";
}

function truncatePosts() {
  document.querySelectorAll(".post-text").forEach((el) => {
    if (el.dataset.processed) return;

    setTimeout(() => {
      el.offsetHeight;
      if (el.scrollHeight > TRUNCATE_HEIGHT) {
        const postId = el.id.replace("post-text-", "");
        const fade = document.getElementById(`fade-overlay-${postId}`);
        const btn = document.querySelector(
          `.see-more-btn[data-post-id="${postId}"]`,
        );

        if (fade && btn) {
          el.style.maxHeight = `${TRUNCATE_HEIGHT}px`;
          el.style.overflow = "hidden";
          el.style.transition = "max-height 0.4s ease-out";
          fade.style.display = "block";

          btn.style.display = "inline-block";
          btn.style.color = "#3b82f6";
          btn.setAttribute("data-expanded", "false");
        }
      }
      el.dataset.processed = "true";
    }, 400);
  });
}

window.toggleReadMore = function (postId, btn) {
  const postText = document.getElementById(`post-text-${postId}`);
  const fade = document.getElementById(`fade-overlay-${postId}`);

  if (!postText) return;

  const isExpanded = btn.getAttribute("data-expanded") === "true";

  if (!isExpanded) {
    postText.style.maxHeight = postText.scrollHeight + 100 + "px";
    if (fade) fade.style.display = "none";
    btn.innerHTML =
      'See Less <i class="fas fa-chevron-up ms-1" style="font-size: 0.8rem;"></i>';
    btn.setAttribute("data-expanded", "true");

    setTimeout(() => {
      postText.style.maxHeight = "none";
    }, 400);
  } else {
    postText.style.maxHeight = `${TRUNCATE_HEIGHT}px`;
    if (fade) fade.style.display = "block";
    btn.innerHTML =
      'Read More <i class="fas fa-chevron-down ms-1" style="font-size: 0.8rem;"></i>';
    btn.setAttribute("data-expanded", "false");

    const card = postText.closest(".card");
    if (card) {
      const yOffset = card.getBoundingClientRect().top + window.scrollY - 80;
      window.scrollTo({ top: yOffset, behavior: "smooth" });
    }
  }
};

function debounce(func, wait) {
  let timeout;
  return function (...args) {
    const context = this;
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(context, args), wait);
  };
}

/* =========================================
   @ MENTIONS AUTO-COMPLETE (COMMENTS) 🚀 NEW
   ========================================= */
function setupMentions() {
  const commentInputs = document.querySelectorAll('.ajax-comment-form input[name="text"]');
  
  commentInputs.forEach(input => {
    // Prevent double-binding on infinite scroll
    if (input.dataset.mentionsBound) return;
    
    const wrapper = input.closest('.input-group');
    // Ensure the dropdown can overflow out of the input group visually
    wrapper.classList.remove('overflow-hidden');
    wrapper.style.overflow = 'visible'; 
    
    // Create the floating dropdown UI
    const dropdown = document.createElement('div');
    dropdown.className = 'mention-dropdown dropdown-menu shadow-lg border-0 fade-in-up';
    dropdown.style.position = 'absolute';
    dropdown.style.display = 'none';
    dropdown.style.bottom = '110%'; // Pop UP above the input line
    dropdown.style.left = '20px';
    dropdown.style.zIndex = '1050';
    dropdown.style.maxHeight = '200px';
    dropdown.style.overflowY = 'auto';
    wrapper.appendChild(dropdown);

    input.addEventListener('input', debounce(async function(e) {
      const cursorPosition = this.selectionStart;
      const textBeforeCursor = this.value.substring(0, cursorPosition);
      const words = textBeforeCursor.split(/\s+/);
      const currentWord = words[words.length - 1];

      // If the user is currently typing a word that starts with @
      if (currentWord.startsWith('@') && currentWord.length > 1) {
        const query = currentWord.substring(1);
        try {
          const response = await fetch(`/api/search-users?q=${query}`);
          const users = await response.json();

          dropdown.innerHTML = '';
          if (users.length > 0) {
            users.forEach(user => {
              const item = document.createElement('a');
              item.className = 'dropdown-item d-flex align-items-center gap-2 py-2';
              item.href = '#';
              
              let avatarHtml = user.profile_pic 
                ? `<img src="/static/uploads/avatars/${user.profile_pic}" class="rounded-circle object-fit-cover shadow-sm border border-secondary" width="24" height="24">`
                : `<div class="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center shadow-sm" style="width:24px; height:24px; font-size:12px;">${user.username.charAt(0).toUpperCase()}</div>`;

              item.innerHTML = `${avatarHtml} <span class="fw-bold" style="color: var(--text-main);">@${user.username}</span>`;
              
              item.onclick = function(ev) {
                ev.preventDefault();
                const textAfterCursor = input.value.substring(cursorPosition);
                const newTextBeforeCursor = textBeforeCursor.substring(0, textBeforeCursor.length - currentWord.length) + `@${user.username} `;
                input.value = newTextBeforeCursor + textAfterCursor;
                dropdown.style.display = 'none';
                input.focus();
              };
              dropdown.appendChild(item);
            });
            dropdown.style.display = 'block';
          } else {
            dropdown.style.display = 'none';
          }
        } catch(err) { console.error(err); }
      } else {
        dropdown.style.display = 'none';
      }
    }, 150));

    // Hide dropdown if clicked outside
    document.addEventListener('click', function(e) {
      if (!wrapper.contains(e.target)) {
        dropdown.style.display = 'none';
      }
    });
    
    input.dataset.mentionsBound = "true";
  });
}

/* =========================================
   MAIN DOM LOAD LOGIC
   ========================================= */
document.addEventListener("DOMContentLoaded", () => {
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
  
  // 🚀 NEW: Trigger global Syntax Highlighting
  if (typeof hljs !== 'undefined') {
    hljs.highlightAll();
  }

  document
    .querySelectorAll("#toastContainer .toast")
    .forEach((t) => new bootstrap.Toast(t, { delay: 3000 }).show());

  truncatePosts();
  setupMentions(); // 🚀 Setup mentions on page load
  
  window.addEventListener("load", truncatePosts);

  const notifBtn = document.getElementById("notifDropdown");
  if (notifBtn) {
    notifBtn.addEventListener("click", () => {
      const badge = document.getElementById("notifBadge");
      if (badge) {
        badge.style.display = "none";
        fetch("/api/mark-notifications-read", {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRFToken": getCsrfToken() },
        }).catch((err) => console.error("Error marking read:", err));
      }
    });
  }

  refreshTimestamps();
  setInterval(refreshTimestamps, 60000);

  const searchInput = document.getElementById("searchInput");
  const searchResults = document.getElementById("searchResults");

  if (searchInput && searchResults) {
    searchInput.addEventListener(
      "input",
      debounce(async function () {
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
      }, 300),
    );

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

  fetch(`/like-post/${postId}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": getCsrfToken() },
  })
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
   SAVE POST LOGIC
   ========================================= */
window.savePost = function (postId, btn) {
  if (btn.dataset.loading === "true") return;
  btn.dataset.loading = "true";

  const icon = btn.querySelector("i");
  const isSaved = icon.classList.contains("fas");

  if (isSaved) {
    icon.classList.remove("fas", "text-primary");
    icon.classList.add("far");
  } else {
    icon.classList.remove("far");
    icon.classList.add("fas", "text-primary");
    icon.style.transform = "scale(1.2)";
    setTimeout(() => (icon.style.transform = "scale(1)"), 200);
  }

  fetch(`/save-post/${postId}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": getCsrfToken() },
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.saved) {
        icon.classList.add("fas", "text-primary");
        icon.classList.remove("far");
        if (typeof showToast === "function")
          showToast("Post saved to your bookmarks!");
      } else {
        icon.classList.add("far");
        icon.classList.remove("fas", "text-primary");
        if (typeof showToast === "function")
          showToast("Post removed from bookmarks.");
      }
    })
    .catch(() => {
      if (typeof showToast === "function") showToast("Network error", true);
    })
    .finally(() => (btn.dataset.loading = "false"));
};

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

  fetch(`/like-comment/${commentId}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": getCsrfToken() },
  })
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
  if (!isoString) return "";

  if (!isoString.endsWith("Z")) isoString += "Z";

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
   USERNAME AVAILABILITY
   ========================================= */
function checkSignupUsername() {
  const usernameInput = document.getElementById("signupUsername");
  const statusDiv = document.getElementById("signupUsernameStatus");
  const submitBtn = document.getElementById("signupSubmitBtn");
  const checkBtn = document.getElementById("checkBtn");

  const username = usernameInput.value.trim();

  if (username.length < 3) {
    statusDiv.innerHTML =
      '<span class="text-danger">Too short (min 3 chars).</span>';
    submitBtn.disabled = true;
    return;
  }

  checkBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  checkBtn.disabled = true;

  fetch("/check-username-signup", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    body: JSON.stringify({ username: username }),
  })
    .then((res) => res.json())
    .then((data) => {
      checkBtn.innerHTML = "Check";
      checkBtn.disabled = false;

      if (data.available) {
        statusDiv.innerHTML = `<span class="text-success"><i class="fas fa-check-circle"></i> ${data.message}</span>`;
        submitBtn.disabled = false;
        usernameInput.classList.remove("is-invalid");
        usernameInput.classList.add("is-valid");
      } else {
        statusDiv.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle"></i> ${data.message}</span>`;
        submitBtn.disabled = true;
        usernameInput.classList.add("is-invalid");
      }
    })
    .catch(() => {
      checkBtn.innerHTML = "Check";
      checkBtn.disabled = false;
      statusDiv.innerHTML =
        '<span class="text-warning">Server error. Try again.</span>';
    });
}

function resetSignupCheck() {
  const submitBtn = document.getElementById("signupSubmitBtn");
  const statusDiv = document.getElementById("signupUsernameStatus");
  const usernameInput = document.getElementById("signupUsername");

  if (submitBtn) submitBtn.disabled = true;
  if (statusDiv)
    statusDiv.innerHTML =
      '<span class="text-muted small">Please check availability.</span>';
  if (usernameInput) usernameInput.classList.remove("is-valid", "is-invalid");
}

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
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
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
   PRELOADER SYSTEM & AJAX LOGIC
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

document.addEventListener("submit", async function (e) {
  const form = e.target;

  if (form.classList.contains("ajax-comment-form")) {
    e.preventDefault();

    const input = form.querySelector('input[name="text"]');
    const btn = form.querySelector('button[type="submit"]');
    const postId = form.getAttribute("data-post-id");

    if (!input || !input.value.trim()) return;

    btn.disabled = true;
    const originalBtnText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    try {
      const formData = new FormData(form);
      await fetch(form.action, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": getCsrfToken() },
        body: formData,
      });

      const postResponse = await fetch(`/post/${postId}`);
      if (postResponse.ok) {
        const html = await postResponse.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");

        const newComments = doc.querySelector(
          `#comments-${postId} .comments-list`,
        );
        const oldComments = document.querySelector(
          `#comments-${postId} .comments-list`,
        );

        if (newComments && oldComments) {
          oldComments.innerHTML = newComments.innerHTML;

          const newCount = doc.querySelector(
            `[data-bs-target="#comments-${postId}"] span`,
          );
          const oldCount = document.querySelector(
            `[data-bs-target="#comments-${postId}"] span`,
          );
          if (newCount && oldCount) oldCount.innerHTML = newCount.innerHTML;

          input.value = "";
          showToast("Comment posted!");
        } else {
          window.location.reload();
        }
      } else {
        showToast("Error retrieving updated comments", true);
      }
    } catch (error) {
      showToast("Network error", true);
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalBtnText;
    }
    return;
  }

  if (e.defaultPrevented) return;
  if (form.id === "chatForm") return;
  if (form.checkValidity()) {
    showLoader();
  }
});

document.addEventListener("click", async function (e) {
  const deleteBtn = e.target.closest(".ajax-delete-comment");
  if (deleteBtn) {
    e.preventDefault();
    if (!confirm("Delete this comment?")) return;

    const postId = deleteBtn.getAttribute("data-post-id");
    const originalText = deleteBtn.innerHTML;

    deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    deleteBtn.style.pointerEvents = "none";

    try {
      await fetch(deleteBtn.href);

      const postResponse = await fetch(`/post/${postId}`);
      if (postResponse.ok) {
        const html = await postResponse.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");

        const newComments = doc.querySelector(
          `#comments-${postId} .comments-list`,
        );
        const oldComments = document.querySelector(
          `#comments-${postId} .comments-list`,
        );

        if (newComments && oldComments) {
          oldComments.innerHTML = newComments.innerHTML;

          const newCount = doc.querySelector(
            `[data-bs-target="#comments-${postId}"] span`,
          );
          const oldCount = document.querySelector(
            `[data-bs-target="#comments-${postId}"] span`,
          );
          if (newCount && oldCount) oldCount.innerHTML = newCount.innerHTML;

          showToast("Comment deleted!");
        } else {
          window.location.reload();
        }
      }
    } catch (err) {
      showToast("Network error", true);
      deleteBtn.innerHTML = originalText;
      deleteBtn.style.pointerEvents = "auto";
    }
    return;
  }

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
      !actionAttr &&
      !target.classList.contains("ajax-delete-comment")
    ) {
      showLoader();
    }
  }
});

/* =========================================
   🚀 NEW: INFINITE SCROLL LOGIC
   ========================================= */
document.addEventListener("DOMContentLoaded", function () {
  const sentinel = document.getElementById("sentinel");

  if (sentinel) {
    let isFetching = false;

    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !isFetching) {
        const hasNext = sentinel.getAttribute("data-has-next") === "true";

        if (hasNext) {
          loadMorePosts();
        } else {
          const spinner = document.getElementById("scroll-spinner");
          const endMessage = document.getElementById("end-message");
          if (spinner) spinner.style.display = "none";
          if (endMessage) endMessage.classList.remove("d-none");
          observer.disconnect(); // Stop observing if no more posts
        }
      }
    }, { rootMargin: "0px 0px 200px 0px" });

    observer.observe(sentinel);

    function loadMorePosts() {
      isFetching = true;
      const spinner = document.getElementById("scroll-spinner");
      if (spinner) spinner.style.display = "inline-block";

      let currentPage = parseInt(sentinel.getAttribute("data-page"));
      let nextPage = currentPage + 1;
      let fetchUrl = `${sentinel.getAttribute("data-url")}?page=${nextPage}`;

      fetch(fetchUrl, {
        headers: {
          "X-Requested-With": "XMLHttpRequest", // Tells Flask this is an AJAX request
        },
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.html) {
            // Insert the new posts right above the sentinel loading spinner
            sentinel.insertAdjacentHTML("beforebegin", data.html);

            // Update the sentinel data for the NEXT time they scroll
            sentinel.setAttribute("data-page", nextPage);
            sentinel.setAttribute("data-has-next", data.has_next ? "true" : "false");

            // Re-initialize "Read More" truncation and Timeago for newly injected posts
            if (typeof truncatePosts === "function") {
              truncatePosts();
            }
            if (typeof refreshTimestamps === "function") {
              refreshTimestamps();
            }
            if (typeof setupMentions === "function") {
              setupMentions();
            }
          }
        })
        .catch((err) => console.error("Error fetching more posts:", err))
        .finally(() => {
          isFetching = false;
          if (spinner) spinner.style.display = "none";
        });
    }
  }
});

/* =========================================
   LIVE SEARCH AUTOCOMPLETE (Desktop & Mobile)
   ========================================= */
document.addEventListener("DOMContentLoaded", function () {
  // 1. Identify Desktop Elements
  const desktopInput = document.getElementById("searchInput");
  const desktopResults = document.getElementById("searchResults");

  // 2. Identify Mobile Elements
  const mobileInput = document.getElementById("mobileSearchInput");
  
  // Create a mobile results dropdown container dynamically if it doesn't exist
  let mobileResults = document.getElementById("mobileSearchResults");
  if (mobileInput && !mobileResults) {
    mobileResults = document.createElement("div");
    mobileResults.id = "mobileSearchResults";
    mobileResults.className = "dropdown-menu w-100 shadow-lg border-0 mt-2";
    mobileResults.style.borderRadius = "16px";
    mobileResults.style.position = "absolute";
    mobileResults.style.top = "100%";
    mobileResults.style.left = "0";
    mobileResults.style.zIndex = "1050";
    
    // Inject it securely under the mobile search wrapper
    const mobileForm = mobileInput.closest("form");
    if (mobileForm) {
      mobileForm.style.position = "relative";
      mobileForm.insertBefore(mobileResults, mobileForm.querySelector(".d-grid"));
    }
  }

  // 3. The Core Autocomplete Function
  function setupLiveSearch(inputEl, resultsEl) {
    if (!inputEl || !resultsEl) return;

    let debounceTimer;

    inputEl.addEventListener("input", function () {
      clearTimeout(debounceTimer);
      const query = this.value.trim();

      // Clear results if the user deletes the text
      if (query.length < 2) {
        resultsEl.classList.remove("show");
        resultsEl.innerHTML = "";
        return;
      }

      // Wait 300ms after the user stops typing to fetch results
      debounceTimer = setTimeout(() => {
        fetch(`/search?q=${encodeURIComponent(query)}`, {
          headers: {
            "X-Requested-With": "XMLHttpRequest" // Tells Flask this is an AJAX call
          }
        })
        .then(res => {
          return res.text(); 
        })
        .then(html => {
          resultsEl.innerHTML = html;
          resultsEl.classList.add("show");
        })
        .catch(err => console.error("Search autocomplete error:", err));
      }, 300);
    });

    // 4. Close the dropdown if the user clicks anywhere else on the screen
    document.addEventListener("click", function(e) {
      if (!inputEl.contains(e.target) && !resultsEl.contains(e.target)) {
        resultsEl.classList.remove("show");
      }
    });
  }

  // Initialize the listener for both inputs!
  setupLiveSearch(desktopInput, desktopResults);
  setupLiveSearch(mobileInput, mobileResults);
});

/* =========================================
   IMAGE & LINK HELPERS
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
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
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

  fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": getCsrfToken() },
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        const allUserButtons = document.querySelectorAll(`button[onclick*="toggleFollow('${userId}'"]`);

        allUserButtons.forEach((userBtn) => {
          if (data.action === "followed") {
            userBtn.innerText = "Following";
            userBtn.classList.remove("btn-primary", "shadow-sm");
            userBtn.classList.add("btn-outline-secondary");
          } else {
            userBtn.innerText = "Follow";
            userBtn.classList.remove("btn-outline-secondary");
            userBtn.classList.add("btn-primary", "shadow-sm");
          }
        });
        
        if (typeof showToast === "function") {
          showToast(data.action === "followed" ? "User followed" : "User unfollowed");
        }
      } else {
        if (typeof showToast === "function") {
          showToast(data.message || "Error processing request", true);
        } else {
          alert(data.message || "Error processing request");
        }
      }
    })
    .catch((err) => {
      console.error("Error:", err);
      if (typeof showToast === "function") showToast("Network error", true);
    });
}

window.addEventListener("pageshow", function (event) {
  var historyTraversal =
    event.persisted ||
    (typeof window.performance != "undefined" &&
      window.performance.navigation.type === 2);
  if (historyTraversal) {
    window.location.reload();
  }
});

/* =========================================
   Drag & Drop Image Upload Logic 
   ========================================= */
document.addEventListener("DOMContentLoaded", function () {
  const dropZones = document.querySelectorAll(".upload-zone-drop");

  dropZones.forEach((zone) => {
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      zone.addEventListener(eventName, preventDefaults, false);
      document.body.addEventListener(eventName, preventDefaults, false);
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      zone.addEventListener(
        eventName,
        () => zone.classList.add("drag-over"),
        false
      );
    });

    ["dragleave", "drop"].forEach((eventName) => {
      zone.addEventListener(
        eventName,
        () => zone.classList.remove("drag-over"),
        false
      );
    });

    zone.addEventListener("drop", handleDrop, false);

    zone.addEventListener("click", () => {
      const fileInput = zone.parentElement.querySelector('input[type="file"]');
      if (fileInput) fileInput.click();
    });
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files && files.length > 0) {
      const droppedFile = files[0];

      if (!droppedFile.type.startsWith("image/")) {
        if (typeof showToast === "function") {
          showToast("Invalid file type. Please upload an image.", true);
        } else {
          alert("Invalid file type. Please upload an image.");
        }
        return;
      }

      const fileInput = this.parentElement.querySelector('input[type="file"]');
      if (fileInput) {
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(droppedFile);
        fileInput.files = dataTransfer.files;

        const event = new Event("change", { bubbles: true });
        fileInput.dispatchEvent(event);
      }
    }
  }
});

/* =========================================
   SAFETY & MODERATION (BLOCK & REPORT) 
   ========================================= */
window.blockUser = function (userId) {
  if (!confirm("Are you sure you want to block this user? They will no longer be able to message you or see your posts.")) return;
  
  fetch(`/block/${userId}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": getCsrfToken() }
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        if (typeof showToast === "function") showToast("User blocked successfully.");
        // Instantly redirect home so they don't stay on the blocked profile
        setTimeout(() => window.location.href = "/", 1000);
      } else {
        if (typeof showToast === "function") showToast(data.message, true);
      }
    });
};

window.unblockUser = function (userId) {
  fetch(`/unblock/${userId}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": getCsrfToken() }
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        location.reload();
      }
    });
};

window.toggleOtherReason = function(itemType, itemId) {
  const select = document.getElementById(`reportReason-${itemType}-${itemId}`);
  const otherDiv = document.getElementById(`otherReasonDiv-${itemType}-${itemId}`);
  if (select && otherDiv) {
    if (select.value === 'Other') {
      otherDiv.classList.remove('d-none');
    } else {
      otherDiv.classList.add('d-none');
    }
  }
};

window.submitReport = function (itemType, itemId) {
  const reasonEl = document.getElementById(`reportReason-${itemType}-${itemId}`);
  let reason = reasonEl ? reasonEl.value : "Inappropriate content";
  
  // Intercept if "Other" is selected to get custom text
  if (reason === 'Other') {
    const otherTextEl = document.getElementById(`otherReasonText-${itemType}-${itemId}`);
    if (otherTextEl && otherTextEl.value.trim() !== '') {
      reason = "Other: " + otherTextEl.value.trim();
    } else {
      if (typeof showToast === "function") showToast("Please specify your reason.", true);
      else alert("Please specify your reason.");
      return; 
    }
  }

  fetch(`/report/${itemType}/${itemId}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { 
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken() 
    },
    body: JSON.stringify({ reason: reason })
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        if (typeof showToast === "function") showToast("Report submitted successfully.");
        const modalEl = document.getElementById(`reportModal-${itemType}-${itemId}`);
        if (modalEl) {
          const modal = bootstrap.Modal.getInstance(modalEl);
          if (modal) modal.hide();
        }
      } else {
        if (typeof showToast === "function") showToast("Error submitting report.", true);
      }
    });
};

/* =========================================
   GLOBAL MODAL FIX (BLURRY SCREEN PREVENTER)
   ========================================= */
document.addEventListener('show.bs.modal', function (event) {
  const modal = event.target;
  if (modal.parentElement !== document.body) {
    document.body.appendChild(modal);
  }
});