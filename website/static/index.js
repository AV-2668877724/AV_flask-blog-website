/* =========================================
   GLOBAL CONFIG & HELPER FUNCTIONS
   ========================================= */

// 🚀 Attach to window so inline scripts (like chat) can access it securely
window.getCsrfToken = function() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute("content") : "";
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
   @ MENTIONS AUTO-COMPLETE (COMMENTS) 
   ========================================= */
function setupMentions() {
  const commentInputs = document.querySelectorAll('.ajax-comment-form input[name="text"]');
  
  commentInputs.forEach(input => {
    if (input.dataset.mentionsBound) return;
    
    const wrapper = input.closest('.input-group');
    wrapper.classList.remove('overflow-hidden');
    wrapper.style.overflow = 'visible'; 
    
    const dropdown = document.createElement('div');
    dropdown.className = 'mention-dropdown dropdown-menu shadow-lg border-0 fade-in-up';
    dropdown.style.position = 'absolute';
    dropdown.style.display = 'none';
    dropdown.style.bottom = '110%'; 
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

              // 🚀 global-nickname support for mentions
              item.innerHTML = `${avatarHtml} <span class="fw-bold global-nickname" data-original-name="${user.username}" style="color: var(--text-main);">@${user.username}</span>`;
              
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
            
            if (typeof window.applyGlobalNicknames === 'function') window.applyGlobalNicknames();
            dropdown.style.display = 'block';
          } else {
            dropdown.style.display = 'none';
          }
        } catch(err) { console.error(err); }
      } else {
        dropdown.style.display = 'none';
      }
    }, 150));

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
  
  const saved = localStorage.getItem("darkMode");
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  if (darkToggle) {
    if (saved === "true" || (saved === null && prefersDark)) {
      setDarkMode(true);
    } else {
      setDarkMode(false);
    }

    darkToggle.addEventListener("click", () => {
      const enabled = document.body.classList.toggle("dark-mode");
      localStorage.setItem("darkMode", enabled);
      setDarkMode(enabled);
    });
  }
  
  if (typeof hljs !== 'undefined') {
    hljs.highlightAll();
  }

  document
    .querySelectorAll("#toastContainer .toast")
    .forEach((t) => new bootstrap.Toast(t, { delay: 3000 }).show());

  setupMentions();
  initReadingProgress(); 

  const notifBtn = document.getElementById("notifDropdown");
  if (notifBtn) {
    notifBtn.addEventListener("click", () => {
      const badge = document.getElementById("notifBadge");
      if (badge) {
        badge.style.display = "none";
        fetch("/api/mark-notifications-read", {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRFToken": window.getCsrfToken() },
        }).catch((err) => console.error("Error marking read:", err));
      }
    });
  }

  refreshTimestamps();
  setInterval(refreshTimestamps, 60000);

  /* =========================================
     🚀 UNIVERSAL LIVE SEARCH SYSTEM
     ========================================= */
  function initUniversalLiveSearch() {
    const searchInputs = document.querySelectorAll('#searchInput, .search-input-field:not(#navMobileSearchInput), .search-input-large');

    searchInputs.forEach(input => {
      if (input.dataset.liveSearchBound) return;
      input.dataset.liveSearchBound = "true";

      let resultsEl = null;
      
      if (input.id === "searchInput") {
        resultsEl = document.getElementById("searchResults");
      } else {
        resultsEl = document.createElement('div');
        resultsEl.className = 'dropdown-menu shadow-lg border-0 position-absolute w-100 mt-2 fade-in-up';
        resultsEl.style.borderRadius = '16px';
        resultsEl.style.top = '100%';
        resultsEl.style.left = '0';
        resultsEl.style.zIndex = '1060';
        resultsEl.style.maxHeight = '250px';
        resultsEl.style.overflowY = 'auto';
        resultsEl.style.display = 'none';
        resultsEl.style.backgroundColor = 'var(--bg-card)';
        
        const wrapper = input.closest('.search-bar-wrapper') || input.closest('.search-input-wrapper') || input.parentElement;
        if (wrapper) {
            wrapper.style.position = 'relative';
            wrapper.appendChild(resultsEl);
        } else {
            input.after(resultsEl);
        }
      }

      if (!resultsEl) return;

      let debounceTimer;

      input.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        const query = this.value.trim();

        if (query.length < 1) {
          resultsEl.classList.remove("show");
          resultsEl.style.display = "none";
          resultsEl.innerHTML = "";
          return;
        }

        debounceTimer = setTimeout(async () => {
          try {
            const response = await fetch(`/api/search-users?q=${query}`);
            if (!response.ok) return;
            
            const users = await response.json();
            resultsEl.innerHTML = "";

            if (users.length > 0) {
              users.forEach((user) => {
                const item = document.createElement("a");
                item.className = "dropdown-item d-flex align-items-center gap-3 py-2 px-3 border-bottom";
                item.href = `/profile/${user.username}`;
                item.style.color = "var(--text-main)";
                item.style.borderColor = "var(--border-color)";

                let avatarHtml = "";
                if (user.profile_pic) {
                  const picSrc = user.profile_pic.startsWith("http") ? user.profile_pic : "/static/uploads/avatars/" + user.profile_pic;
                  avatarHtml = `<img src="${picSrc}" class="rounded-circle object-fit-cover shadow-sm border border-secondary" style="width: 35px; height: 35px;">`;
                } else {
                  avatarHtml = `<div class="d-flex align-items-center justify-content-center bg-primary text-white rounded-circle shadow-sm" style="width: 35px; height: 35px; font-size: 1rem; font-weight: bold;">${user.username.charAt(0).toUpperCase()}</div>`;
                }

                // 🚀 global-nickname support for live search results
                item.innerHTML = `${avatarHtml} <span class="fw-bold global-nickname" data-original-name="${user.username}" style="font-size: 1.05rem;">${user.username}</span>`;
                resultsEl.appendChild(item);
              });
              
              if (typeof window.applyGlobalNicknames === 'function') window.applyGlobalNicknames();
              
              resultsEl.classList.add("show");
              resultsEl.style.display = "block";
            } else {
              resultsEl.innerHTML = `<div class="p-3 text-center text-muted small">No users found.</div>`;
              resultsEl.classList.add("show");
              resultsEl.style.display = "block";
            }
          } catch (error) {
            console.error("Live Search Error:", error);
          }
        }, 300);
      });

      input.addEventListener("keypress", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          window.location.href = `/search-page?q=${encodeURIComponent(this.value.trim())}`;
        }
      });

      document.addEventListener("click", function (e) {
        if (!input.contains(e.target) && !resultsEl.contains(e.target)) {
          resultsEl.classList.remove("show");
          resultsEl.style.display = "none";
        }
      });
    });
  }

  initUniversalLiveSearch();

  const usernameInputs = document.querySelectorAll('input[name="username"]');
  usernameInputs.forEach((input) => {
    input.addEventListener("keypress", function (e) {
      const regex = /[a-zA-Z0-9_.]/;
      if (!regex.test(e.key)) {
        e.preventDefault();
      }
    });
  });

 /* =========================================
     GLOBAL SKELETON UI CONTROLLER 
     ========================================= */
  window.initSkeletons = function() {
    setTimeout(() => {
      document.querySelectorAll('.skeleton-ui-wrapper').forEach(skeleton => {
        skeleton.style.opacity = '0';
        setTimeout(() => {
          skeleton.style.display = 'none';
        }, 300); 
      });
      
      document.querySelectorAll('.skeleton-ui-content').forEach(content => {
        content.classList.remove('d-none');
        content.classList.add('fade-in-up'); 
      });
    }, 400); 
  };

  initSkeletons();
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

window.showToast = function(message, isError = false) {
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
   READING PROGRESS TRACKER 
   ========================================= */
function initReadingProgress() {
  document.querySelectorAll('.post-text').forEach(postEl => {
    const postId = postEl.id.replace('post-text-', '');
    const progress = localStorage.getItem(`reading_progress_${postId}`);
    
    if (progress) {
      const progressBar = document.getElementById(`read-progress-${postId}`);
      const badge = document.getElementById(`continue-badge-${postId}`);
      
      if (progressBar) {
        progressBar.style.width = `${progress}%`;
        progressBar.parentElement.style.display = 'block'; 
      }
      if (badge && progress > 0 && progress < 100) {
        badge.style.display = 'inline-flex';
      }
    }
  });

  window.addEventListener('scroll', debounce(() => {
    document.querySelectorAll('.post-text').forEach(postEl => {
      if (postEl.style.maxHeight !== 'none' && !postEl.classList.contains('full-post')) return;

      const rect = postEl.getBoundingClientRect();
      const windowHeight = window.innerHeight;
      
      if (rect.top < windowHeight && rect.bottom > 0) {
        const scrolled = windowHeight - rect.top;
        const total = rect.height;
        let percent = Math.floor((scrolled / total) * 100);
        
        if (percent > 100) percent = 100;
        if (percent < 0) percent = 0;

        const postId = postEl.id.replace('post-text-', '');
        const currentSaved = parseInt(localStorage.getItem(`reading_progress_${postId}`) || '0', 10);
        
        if (percent > currentSaved) {
          localStorage.setItem(`reading_progress_${postId}`, percent);
          const progressBar = document.getElementById(`read-progress-${postId}`);
          const badge = document.getElementById(`continue-badge-${postId}`);
          
          if (progressBar) {
            progressBar.parentElement.style.display = 'block';
            progressBar.style.width = `${percent}%`;
          }
          if (badge) {
            if (percent < 100) {
              badge.style.display = 'inline-flex';
            } else {
              badge.style.display = 'none';
            }
          }
        }
      }
    });
  }, 100)); 
}

/* =========================================
   LIKE POST LOGIC
   ========================================= */
window.likePost = function(postId, btn) {
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
    headers: { "X-CSRFToken": window.getCsrfToken() },
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
    .catch(() => window.showToast("Network error", true))
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
    headers: { "X-CSRFToken": window.getCsrfToken() },
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.saved) {
        icon.classList.add("fas", "text-primary");
        icon.classList.remove("far");
        if (typeof window.showToast === "function")
          window.showToast("Post saved to your bookmarks!");
      } else {
        icon.classList.add("far");
        icon.classList.remove("fas", "text-primary");
        if (typeof window.showToast === "function")
          window.showToast("Post removed from bookmarks.");
      }
    })
    .catch(() => {
      if (typeof window.showToast === "function") window.showToast("Network error", true);
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

window.likeComment = function(commentId, btn) {
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
    headers: { "X-CSRFToken": window.getCsrfToken() },
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

window.refreshTimestamps = function() {
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
window.checkSignupUsername = function() {
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
      "X-CSRFToken": window.getCsrfToken(),
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

window.resetSignupCheck = function() {
  const submitBtn = document.getElementById("signupSubmitBtn");
  const statusDiv = document.getElementById("signupUsernameStatus");
  const usernameInput = document.getElementById("signupUsername");

  if (submitBtn) submitBtn.disabled = true;
  if (statusDiv)
    statusDiv.innerHTML =
      '<span class="text-muted small">Please check availability.</span>';
  if (usernameInput) usernameInput.classList.remove("is-valid", "is-invalid");
}

window.checkUsername = function() {
  const input = document.getElementById("newUsername");
  const status = document.getElementById("usernameStatus");
  const submitBtn = document.getElementById("submitUsernameBtn");
  const username = input.value.trim();

  if (!username) {
    status.textContent = "Please enter a username";
    status.className = "text-danger";
    submitBtn.disabled = true;
    return;
  }

  fetch("/check-username", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": window.getCsrfToken(),
    },
    body: JSON.stringify({ username }),
  })
    .then((res) => res.json())
    .then((data) => {
      status.textContent = data.message;
      if (data.available) {
        status.className = "text-success";
        submitBtn.disabled = false;
        document.getElementById("finalUsername").value = username;
      } else {
        status.className = "text-danger";
        submitBtn.disabled = true;
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
        headers: { "X-CSRFToken": window.getCsrfToken() },
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
          
          if (typeof window.applyGlobalNicknames === 'function') {
              window.applyGlobalNicknames();
          }

          window.showToast("Comment posted!");
        } else {
          window.location.reload();
        }
      } else {
        window.showToast("Error retrieving updated comments", true);
      }
    } catch (error) {
      window.showToast("Network error", true);
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

          if (typeof window.applyGlobalNicknames === 'function') {
              window.applyGlobalNicknames();
          }

          window.showToast("Comment deleted!");
        } else {
          window.location.reload();
        }
      }
    } catch (err) {
      window.showToast("Network error", true);
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
   INFINITE SCROLL LOGIC
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
          observer.disconnect(); 
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
          "X-Requested-With": "XMLHttpRequest", 
        },
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.html) {
            sentinel.insertAdjacentHTML("beforebegin", data.html);

            sentinel.setAttribute("data-page", nextPage);
            sentinel.setAttribute("data-has-next", data.has_next ? "true" : "false");

            if (typeof window.refreshTimestamps === "function") {
              window.refreshTimestamps();
            }
            if (typeof setupMentions === "function") {
              setupMentions();
            }
            if (typeof initReadingProgress === "function") {
              initReadingProgress(); 
            }
            if (typeof window.applyGlobalNicknames === "function") {
              window.applyGlobalNicknames();
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
   IMAGE, LINK & SHARE HELPERS
   ========================================= */
window.shareContent = function(title, url) {
    if (navigator.share) {
        navigator.share({
            title: title,
            url: url
        }).catch(console.error);
    } else {
        navigator.clipboard.writeText(url).then(() => {
            if (typeof window.showToast === 'function') window.showToast("Link copied to clipboard!");
            else alert("Link copied to clipboard!");
        });
    }
};

window.previewImage = function(input, imgId) {
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

window.viewFullSize = function(src) {
  const modal = new bootstrap.Modal(document.getElementById("imageViewModal"));
  const img = document.getElementById("fullSizeImage");
  img.src = src;
  modal.show();
}

window.removeSocialLink = function(url) {
  if (!confirm("Remove this link?")) return;

  fetch("/profile/remove-social", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": window.getCsrfToken(),
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

window.toggleFollow = function(userId, btn) {
  const isFollowing = btn.innerText.trim() === "Following";
  const url = isFollowing ? `/unfollow/${userId}` : `/follow/${userId}`;

  fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": window.getCsrfToken() },
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
        
        if (typeof window.showToast === "function") {
          window.showToast(data.action === "followed" ? "User followed" : "User unfollowed");
        }
      } else {
        if (typeof window.showToast === "function") {
          window.showToast(data.message || "Error processing request", true);
        } else {
          alert(data.message || "Error processing request");
        }
      }
    })
    .catch((err) => {
      console.error("Error:", err);
      if (typeof window.showToast === "function") window.showToast("Network error", true);
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
        if (typeof window.showToast === "function") {
          window.showToast("Invalid file type. Please upload an image.", true);
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
    headers: { "X-CSRFToken": window.getCsrfToken() }
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        if (typeof window.showToast === "function") window.showToast("User blocked successfully.");
        setTimeout(() => window.location.href = "/", 1000);
      } else {
        if (typeof window.showToast === "function") window.showToast(data.message, true);
      }
    });
};

window.unblockUser = function (userId) {
  fetch(`/unblock/${userId}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": window.getCsrfToken() }
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
  
  if (reason === 'Other') {
    const otherTextEl = document.getElementById(`otherReasonText-${itemType}-${itemId}`);
    if (otherTextEl && otherTextEl.value.trim() !== '') {
      reason = "Other: " + otherTextEl.value.trim();
    } else {
      if (typeof window.showToast === "function") window.showToast("Please specify your reason.", true);
      else alert("Please specify your reason.");
      return; 
    }
  }

  fetch(`/report/${itemType}/${itemId}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { 
      "Content-Type": "application/json",
      "X-CSRFToken": window.getCsrfToken() 
    },
    body: JSON.stringify({ reason: reason })
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        if (typeof window.showToast === "function") window.showToast("Report submitted successfully.");
        const modalEl = document.getElementById(`reportModal-${itemType}-${itemId}`);
        if (modalEl) {
          const modal = bootstrap.Modal.getInstance(modalEl);
          if (modal) modal.hide();
        }
      } else {
        if (typeof window.showToast === "function") window.showToast("Error submitting report.", true);
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

/* =========================================
   SMART EMAIL APP ROUTER
   ========================================= */
window.openSmartMail = function(service, email, subject, body) {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    
    const gmailWeb = `https://mail.google.com/mail/?view=cm&fs=1&to=${email}&su=${subject}&body=${body}`;
    const zohoWeb = `https://mail.zoho.in/zm/#compose?to=${email}&subject=${subject}&content=${body}`;

    if (isMobile) {
        window.location.href = `mailto:${email}?subject=${subject}&body=${body}`;
    } else {
        if (service === 'gmail') {
            window.open(gmailWeb, '_blank');
        } else if (service === 'zoho') {
            window.open(zohoWeb, '_blank');
        }
    }
};