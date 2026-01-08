// index.js
// Dark mode, see more/less, likes, toasts, global search, timestamps

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
     POST TRUNCATION
  ========================== */
  document.querySelectorAll(".post-text").forEach((el) => {
    const overlay = el.parentElement.querySelector(".fade-overlay");
    if (el.scrollHeight > 150) {
      if (overlay) overlay.style.display = "block";
      el.style.maxHeight = "150px";
      el.style.overflow = "hidden";
    }
  });

  /* =========================
     SEE MORE / SEE LESS
  ========================== */
  document.querySelectorAll(".see-more-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const postId = btn.dataset.postId;
      const postText = document.getElementById(`post-text-${postId}`);
      const overlay = document.getElementById(`fade-overlay-${postId}`);

      if (!postText) return;

      if (btn.innerText === "See More") {
        postText.style.maxHeight = "none";
        postText.style.overflow = "visible";
        btn.innerText = "See Less";
        if (overlay) overlay.style.display = "none";
      } else {
        postText.style.maxHeight = "150px";
        postText.style.overflow = "hidden";
        btn.innerText = "See More";
        if (overlay) overlay.style.display = "block";

        const rect = btn.getBoundingClientRect();
        window.scrollTo({
          top: window.scrollY + rect.top - 100,
          behavior: "smooth",
        });
      }
    });
  });

  /* =========================
     🔍 GLOBAL SEARCH
  ========================== */
  const searchInput = document.getElementById("searchInput");
  const searchResults = document.getElementById("searchResults");
  let timeout;

  if (searchInput && searchResults) {
    searchInput.addEventListener("input", () => {
      clearTimeout(timeout);
      const query = searchInput.value.trim();

      if (query.length < 2) {
        searchResults.style.display = "none";
        return;
      }

      timeout = setTimeout(() => {
        fetch(`/search?q=${encodeURIComponent(query)}`)
          .then((res) => res.json())
          .then((data) => {
            searchResults.innerHTML = "";

            if (data.users && data.users.length > 0) {
              data.users.forEach((user) => {
                const item = document.createElement("a");
                item.className = "dropdown-item";
                item.href = `/search-page?q=${encodeURIComponent(
                  user.username
                )}`;
                item.innerHTML = `<strong>${user.username}</strong>`;
                searchResults.appendChild(item);
              });
              searchResults.style.display = "block";
            } else {
              searchResults.style.display = "none";
            }
          })
          .catch(() => {
            searchResults.style.display = "none";
          });
      }, 300);
    });

    // ENTER → full search page
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (query.length >= 2) {
          window.location.href = `/search-page?q=${encodeURIComponent(query)}`;
        }
      }
    });

    // Outside click close
    document.addEventListener("click", (e) => {
      if (
        !searchInput.contains(e.target) &&
        !searchResults.contains(e.target)
      ) {
        searchResults.style.display = "none";
      }
    });
  }

  /* =========================
     TIMESTAMP REFRESH
  ========================== */
  refreshTimestamps();
  setInterval(refreshTimestamps, 60000);
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

  const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
  bsToast.show();
  toast.addEventListener("hidden.bs.toast", () => toast.remove());
}

/* =========================
   👍 LIKE HANDLER (SAFE)
========================== */
function like(postId) {
  const countEl = document.getElementById(`likes-count-${postId}`);
  const btn = document.getElementById(`like-button-${postId}`);
  if (!countEl || !btn) return;

  if (btn.dataset.loading === "true") return;
  btn.dataset.loading = "true";

  const liked = btn.classList.contains("far");
  const current = parseInt(countEl.innerText, 10) || 0;

  // Optimistic UI
  countEl.innerText = liked ? current + 1 : Math.max(0, current - 1);
  btn.classList.toggle("far");
  btn.classList.toggle("fas");
  btn.classList.toggle("text-primary");

  fetch(`/like-post/${postId}`, { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      countEl.innerText = data.likes;
      if (data.liked) {
        btn.classList.add("fas", "text-primary");
        btn.classList.remove("far");
      } else {
        btn.classList.add("far");
        btn.classList.remove("fas", "text-primary");
      }
    })
    .catch(() => showToast("Network error", true))
    .finally(() => (btn.dataset.loading = "false"));
}

/* =========================
   ⏱️ TIME AGO SUPPORT
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
