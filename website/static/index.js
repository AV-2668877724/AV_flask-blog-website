// index.js - improved optimistic likes, toasts, search, dark mode

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

  // Live search (client-side)
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      document.querySelectorAll('.card .post-text').forEach(card => {
        const text = card.innerText.toLowerCase();
        card.closest('.card').style.display = text.includes(q) ? '' : 'none';
      });
    });
  }
});

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
