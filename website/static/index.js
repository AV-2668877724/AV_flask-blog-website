/* =========================
     GLOBAL CONFIG & HELPER FUNCTIONS
   ========================== */
const TRUNCATE_HEIGHT = 400; // ✅ Your preferred height

// 1. Truncate posts (Global function so Infinite Scroll can use it)
function truncatePosts() {
  document.querySelectorAll(".post-text").forEach((el) => {
    // Only truncate if we haven't already processed it
    if (el.dataset.processed) return;

    const overlay = el.parentElement.querySelector(".fade-overlay");
    if (el.scrollHeight > TRUNCATE_HEIGHT) {
      if (overlay) overlay.style.display = "block";
      el.style.maxHeight = `${TRUNCATE_HEIGHT}px`;
      el.style.overflow = "hidden";
    }
    el.dataset.processed = "true"; // Mark as done
  });
}

document.addEventListener("DOMContentLoaded", () => {
  /* =========================
       DARK MODE
    ========================== */
  const darkToggle = document.getElementById("darkToggle");
  const saved = localStorage.getItem("darkMode") === "true";

  // Auth-only dark mode button safety
  if (darkToggle) {
    setDarkMode(saved);

    darkToggle.addEventListener("click", () => {
      const enabled = document.body.classList.toggle("dark-mode");
      localStorage.setItem("darkMode", enabled);
      setDarkMode(enabled);
    });
  } else {
    // Force light mode on auth pages
    document.body.classList.remove("dark-mode");
  }

  /* =========================
       AUTO TOAST SHOW (FLASH)
    ========================== */
  document
    .querySelectorAll("#toastContainer .toast")
    .forEach((t) => new bootstrap.Toast(t, { delay: 3000 }).show());

  /* =========================
       POST TRUNCATION (ON LOAD)
    ========================== */
  // Run on startup for existing posts
  truncatePosts();

  /* =========================
       READ MORE / READ LESS (EVENT DELEGATION)
    ========================== */
  document.addEventListener("click", function (e) {
    // Check if the clicked element is our button
    if (e.target && e.target.classList.contains("see-more-btn")) {
      const btn = e.target;
      const postId = btn.dataset.postId;
      const postText = document.getElementById(`post-text-${postId}`);
      const overlay = document.getElementById(`fade-overlay-${postId}`);

      if (!postText) return;

      // ✅ FIX: Check for "Read More" (matches your HTML), not "See More"
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

        // Scroll back up slightly so user isn't lost
        const rect = btn.getBoundingClientRect();
        window.scrollTo({
          top: window.scrollY + rect.top - 100,
          behavior: "smooth",
        });
      }
    }
  });

  /* =========================
       NOTIFICATION BADGE LOGIC
    ========================== */
  const notifBtn = document.getElementById("notifDropdown");
  if (notifBtn) {
    notifBtn.addEventListener("click", () => {
      const badge = document.getElementById("notifBadge");
      if (badge) {
        // 1. Visual Hide
        badge.style.display = "none";
        // 2. Backend Sync
        fetch("/api/mark-notifications-read", { method: "POST" }).catch((err) =>
          console.error("Error marking read:", err)
        );
      }
    });
  }

  /* =========================
       TIMESTAMP REFRESH
    ========================== */
  refreshTimestamps();
  setInterval(refreshTimestamps, 60000);

  /* =========================
       LIVE SEARCH (AUTOCOMPLETE)
    ========================== */
  const searchInput = document.getElementById("searchInput");
  const searchResults = document.getElementById("searchResults");

  if (searchInput && searchResults) {
    // 1. Listen for typing (Live Dropdown)
    searchInput.addEventListener("input", async function () {
      const query = this.value.trim();

      // If empty, hide dropdown
      if (query.length < 1) {
        searchResults.classList.remove("show");
        return;
      }

      try {
        // 2. Fetch data from Python API
        const response = await fetch(`/api/search-users?q=${query}`);
        const users = await response.json();

        // 3. Clear previous results
        searchResults.innerHTML = "";

        if (users.length > 0) {
          // 4. Create Dropdown Items
          users.forEach((user) => {
            const item = document.createElement("a");
            item.className =
              "dropdown-item d-flex align-items-center gap-2 py-2";
            item.href = `/profile/${user.username}`; // Link to profile

            // Handle Avatar
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

          // Show the dropdown
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

    // 5. Handle "Enter" key to go to full search page
    searchInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        window.location.href = `/search-page?q=${this.value}`;
      }
    });

    // 6. Hide dropdown when clicking outside
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

  /* =======================================================
     ✅ CRITICAL FIX: RESET UPDATE BUTTON ON TYPING
     ======================================================= */
  const newUsernameInput = document.getElementById("newUsername");
  const submitUsernameBtn = document.getElementById("submitUsernameBtn");
  const usernameStatus = document.getElementById("usernameStatus");

  if (newUsernameInput && submitUsernameBtn) {
    newUsernameInput.addEventListener("input", function() {
      // 1. Immediately Disable the button if user types anything
      submitUsernameBtn.disabled = true;
      
      // 2. Clear the "Available" message so user knows they must check again
      if (usernameStatus) {
        usernameStatus.textContent = "";
        usernameStatus.className = "";
      }
    });
  }
});

/* =========================
   DARK MODE HELPER
========================== */
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

/* =========================
   TOAST HELPER
========================== */
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
      <button type="button" class="btn-close btn-close-white me-2 m-auto"
              data-bs-dismiss="toast"></button>
    </div>`;
  container.appendChild(toast);

  const bsToast = new bootstrap.Toast(toast, {
    delay: 3000,
  });
  bsToast.show();
  toast.addEventListener("hidden.bs.toast", () => toast.remove());
}

/* =========================
   👍 LIKE HANDLER (WITH ANIMATION)
========================== */
function likePost(postId, btn) {
  like(postId);
}

function like(postId) {
  const countEl = document.getElementById(`likes-count-${postId}`);
  const btn = document.getElementById(`like-button-${postId}`);
  const icon = btn ? (btn.querySelector("i") || btn) : null;

  if (!countEl || !btn) return;

  if (btn.dataset.loading === "true") return;
  btn.dataset.loading = "true";

  // Check state
  const isFar = icon.classList.contains("far"); // currently empty (unliked)
  const current = parseInt(countEl.innerText, 10) || 0;

  // --- OPTIMISTIC UI UPDATE ---
  if (isFar) {
    // 1. User is LIKING the post
    countEl.innerText = current + 1;
    
    icon.classList.remove("far");
    icon.classList.add("fas", "text-danger"); // Use Red for Heart
    
    // 🔥 TRIGGER ANIMATION (Confetti + Pop)
    btn.classList.add("like-anim");
    
    // Remove animation class after it finishes so it can play again later
    setTimeout(() => {
      btn.classList.remove("like-anim");
    }, 600);

  } else {
    // 2. User is UNLIKING
    countEl.innerText = Math.max(0, current - 1);
    icon.classList.remove("fas", "text-danger");
    icon.classList.add("far");
  }

  // --- SEND TO SERVER ---
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

/* =========================
   💬 COMMENT RIPPLE HANDLER
========================== */
document.addEventListener("click", function(e) {
    // Look for comment buttons (or links that look like buttons)
    const btn = e.target.closest(".btn-comment, .comment-btn-trigger");
    
    if (btn) {
        // Add ripple effect classes
        btn.classList.add("ripple-effect", "ripple-active");
        
        // Remove after animation triggers
        setTimeout(() => {
            btn.classList.remove("ripple-active");
        }, 500);
    }
});

/* =========================
  TIME AGO SUPPORT
========================== */
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

// * ADMIN DASHBOARD SEARCH

// Expose to HTML inline handlers
window.handleEnterSearch = function (event, sectionId, value) {
  const section = document.getElementById(sectionId);
  const info = document.getElementById(sectionId + "-info");
  if (!section) return;

  if (event.key === "Enter") {
    event.preventDefault();

    if (!section.classList.contains("show")) {
      new bootstrap.Collapse(section, {
        show: true,
      });
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
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
    }),
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

let signupUsernameValid = false;

function checkSignupUsername() {
  const input = document.getElementById("signupUsername");
  const status = document.getElementById("signupUsernameStatus");
  const submitBtn = document.getElementById("signupSubmitBtn");

  const username = input.value.trim();

  if (!username) {
    status.textContent = "Username is required";
    status.className = "text-danger";
    submitBtn.disabled = true;
    signupUsernameValid = false;
    return;
  }

  fetch("/check-username-signup", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      status.textContent = data.message;

      if (data.available) {
        status.className = "text-success";
        submitBtn.disabled = false;
        signupUsernameValid = true;
      } else {
        status.className = "text-danger";
        submitBtn.disabled = true;
        signupUsernameValid = false;
      }
    });
}

// ================= SOCIAL LINK REMOVE (AJAX) =================
document.addEventListener("click", function (e) {
  const btn = e.target.closest(".remove-social-btn");
  if (!btn) return;

  const url = btn.dataset.url;
  if (!url) return;

  if (!confirm("Remove this link?")) return;

  fetch("/profile/remove-social", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify({
      url,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        const wrapper = btn.closest(".btn-group");
        if (wrapper) wrapper.remove();
      } else {
        alert(data.message || "Failed to remove link.");
      }
    })
    .catch(() => {
      alert("Network error. Please try again.");
    });
});
// ================= FOLLOW BUTTON (LIST PAGES) =================
document.addEventListener("click", function (e) {
  const btn = e.target.closest(".follow-btn");
  if (!btn) return;

  const userId = btn.dataset.userId;
  if (!userId) return;

  btn.disabled = true;

  fetch(`/follow/${userId}`, {
    method: "POST",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        btn.textContent = "Following";
        btn.classList.remove("btn-primary");
        btn.classList.add("btn-outline-secondary");
      } else {
        btn.disabled = false;
      }
    })
    .catch(() => {
      btn.disabled = false;
      alert("Network error");
    });
});

// ================= UNFOLLOW BUTTON =================
document.addEventListener("click", function (e) {
  const btn = e.target.closest(".unfollow-btn");
  if (!btn) return;

  const userId = btn.dataset.userId;
  if (!userId) return;

  if (!confirm("Unfollow this user?")) return;

  btn.disabled = true;

  fetch(`/unfollow/${userId}`, {
    method: "POST",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        btn.textContent = "Follow";
        btn.classList.remove("btn-outline-danger", "unfollow-btn");
        btn.classList.add("btn-primary", "follow-btn");
        btn.disabled = false;
      } else {
        btn.disabled = false;
      }
    })
    .catch(() => {
      btn.disabled = false;
      alert("Network error");
    });
});

/* =========================================
   PROFILE IMAGE VIEWER (LIGHTBOX)
   ========================================= */
function viewFullSize(src) {
  const imgElement = document.getElementById("fullSizeImage");
  const modalElement = document.getElementById("imageViewModal");

  if (imgElement && modalElement) {
    imgElement.src = src;
    const myModal = new bootstrap.Modal(modalElement);
    myModal.show();
  }
}

// ==========================================
//  PRELOADER LOGIC (FIXED)
// ==========================================

const loader = document.getElementById("preloader");

// 1. Hide Loader when page is fully loaded
window.addEventListener("load", function () {
  setTimeout(() => {
    if (loader) loader.classList.add("loader-hidden");
  }, 300);
});

// 2. Show Loader when navigating to a new page (Links only)
document.addEventListener("click", function (e) {
  const target = e.target.closest("a");

  if (target) {
    const href = target.getAttribute("href");
    const targetAttr = target.getAttribute("target");
    const toggleAttr = target.getAttribute("data-bs-toggle");
    const dismissAttr = target.getAttribute("data-bs-dismiss");

    // Check valid link
    if (
      href &&
      !href.startsWith("#") &&
      !href.startsWith("javascript") &&
      targetAttr !== "_blank" &&
      !toggleAttr &&
      !dismissAttr
    ) {
      if (loader) loader.classList.remove("loader-hidden");
    }
  }
});

// 3. Show Loader ONLY on Form SUBMIT (Not just clicking inside)
// ✅ This prevents the loader from showing when typing
document.addEventListener("submit", function (e) {
  const form = e.target;
  // Only show if the form is valid
  if (form.checkValidity()) {
    if (loader) loader.classList.remove("loader-hidden");
  }
});

// ==========================================
//  INFINITE SCROLL LOGIC
// ==========================================

document.addEventListener("DOMContentLoaded", function () {
  const sentinel = document.getElementById("sentinel");
  const container = document.getElementById("posts-container");
  const spinner = document.getElementById("scroll-spinner");
  const endMessage = document.getElementById("end-message");

  // Only run if the sentinel exists (i.e., there are posts)
  if (sentinel) {
    let isLoading = false;

    const observer = new IntersectionObserver(
      (entries) => {
        // Read current state from DOM attributes
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

        // ✅ FIX: Apply truncation to newly loaded posts
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