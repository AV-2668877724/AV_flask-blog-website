// index.js - dark mode, see more/less toggle, likes, toasts

document.addEventListener('DOMContentLoaded', () => {
  // Dark mode toggle
  const darkToggle = document.getElementById('darkToggle');
  const saved = localStorage.getItem('darkMode') === 'true';
  setDarkMode(saved);
  darkToggle?.addEventListener('click', () => {
    const enabled = document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', enabled);
    setDarkMode(enabled);
  });

  // Show overlay initially for truncated posts
  document.querySelectorAll('.post-text').forEach(el => {
    const overlay = el.parentElement.querySelector('.fade-overlay');
    if (el.scrollHeight > 150) {
      if (overlay) overlay.style.display = 'block';
      el.style.maxHeight = '150px';
      el.style.overflow = 'hidden';
    }
  });

  // See More / See Less toggle
  document.querySelectorAll('.see-more-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const postId = btn.dataset.postId;
      const postTextEl = document.getElementById(`post-text-${postId}`);
      const fadeOverlayEl = document.getElementById(`fade-overlay-${postId}`);

      if (!postTextEl) return;

      if (btn.innerText === 'See More') {
        postTextEl.style.maxHeight = 'none';
        postTextEl.style.overflow = 'visible';
        btn.innerText = 'See Less';
        if (fadeOverlayEl) fadeOverlayEl.style.display = 'none';
      } else {
        postTextEl.style.maxHeight = '150px';
        postTextEl.style.overflow = 'hidden';
        btn.innerText = 'See More';
        if (fadeOverlayEl) fadeOverlayEl.style.display = 'block';

        // Scroll back to the button itself smoothly
        const rect = btn.getBoundingClientRect();
        const scrollTop = window.scrollY + rect.top;
        window.scrollTo({ top: scrollTop - 100, behavior: 'smooth' });
      }
    });
  });
});

// Dark mode helper
function setDarkMode(enabled) {
  const icon = document.querySelector('#darkToggle i');
  if (enabled) {
    document.body.classList.add('dark-mode');
    if (icon) { icon.className = 'fas fa-sun'; }
  } else {
    document.body.classList.remove('dark-mode');
    if (icon) { icon.className = 'fas fa-moon'; }
  }
}

// Toast helper
function showToast(message, isError=false) {
  const container = document.getElementById('toastContainer');
  const toastEl = document.createElement('div');
  toastEl.className = `toast align-items-center text-bg-${isError ? 'danger' : 'success'} border-0`;
  toastEl.setAttribute('role', 'alert');
  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
  container.appendChild(toastEl);
  const bsToast = new bootstrap.Toast(toastEl, { delay: 3000 });
  bsToast.show();
  toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

// Optimistic like function
function like(postId) {
  const likeCountEl = document.getElementById(`likes-count-${postId}`);
  const likeButton = document.getElementById(`like-button-${postId}`);
  if (!likeCountEl || !likeButton) return;

  // Prevent double clicks
  if (likeButton.dataset.loading === 'true') return;
  likeButton.dataset.loading = 'true';
  likeButton.classList.add('opacity-50');

  // Optimistic update
  const likedNow = likeButton.classList.contains('far') ? true : false;
  const current = parseInt(likeCountEl.innerText || '0', 10);
  likeCountEl.innerText = likedNow ? current + 1 : Math.max(0, current - 1);
  likeButton.classList.toggle('far');
  likeButton.classList.toggle('fas');
  likeButton.classList.toggle('text-primary');

  fetch(`/like-post/${postId}`, { method: 'POST' })
    .then(res => res.json().then(data => ({ ok: res.ok, data })))
    .then(({ ok, data }) => {
      if (!ok || data.error) {
        // Revert optimistic update
        const reverted = likedNow ? current : Math.max(0, current - 1);
        likeCountEl.innerText = reverted;
        likeButton.classList.toggle('far');
        likeButton.classList.toggle('fas');
        likeButton.classList.toggle('text-primary');
        showToast(data.error || 'Could not update like', true);
      } else {
        // Sync with server values
        likeCountEl.innerText = data.likes;
        if (data.liked) {
          likeButton.classList.add('fas', 'text-primary');
          likeButton.classList.remove('far');
        } else {
          likeButton.classList.add('far');
          likeButton.classList.remove('fas', 'text-primary');
        }
      }
    })
    .catch((err) => {
      // Revert on network error
      const currentVal = parseInt(likeCountEl.innerText || '0', 10);
      likeCountEl.innerText = Math.max(0, currentVal - (likedNow ? 1 : -1));
      likeButton.classList.toggle('far');
      likeButton.classList.toggle('fas');
      likeButton.classList.toggle('text-primary');
      showToast('Network error', true);
      console.error(err);
    })
    .finally(() => {
      likeButton.dataset.loading = 'false';
      likeButton.classList.remove('opacity-50');
    });
}
