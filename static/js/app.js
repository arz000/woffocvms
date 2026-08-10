// CSRF Token Extractor from Cookie Storage
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Escape HTML Strings to Prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
}

/* ==========================================================================
   LOGOUT MODAL
   ========================================================================== */

function openLogoutModal() {
    const modal = document.getElementById("logoutModal");
    if (modal) {
        modal.classList.remove("hidden");
        modal.classList.add("flex");
    }
}

function closeLogoutModal() {
    const modal = document.getElementById("logoutModal");
    if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }
}

const logoutModal = document.getElementById("logoutModal");
if (logoutModal) {
    logoutModal.addEventListener("click", function (e) {
        if (e.target === this) {
            closeLogoutModal();
        }
    });
}

/* ==========================================================================
   CREATE POST MODAL
   ========================================================================== */

function openCreatePostModal() {
    const modal = document.getElementById("createPostModal");
    if (modal) {
        modal.classList.remove("hidden");
        modal.classList.add("flex");
    }
}

function closeCreatePostModal() {
    const modal = document.getElementById("createPostModal");
    if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }
}

/* ==========================================================================
   COMMENT MODAL
   ========================================================================== */

let activePostId = null;

function openCommentModal(postId) {
    activePostId = postId;
    const modal = document.getElementById('commentModal');
    const commentsList = document.getElementById('modalCommentsList');
    
    const form = document.getElementById('modalCommentForm');
    if (form) form.action = `/comment-post/${postId}/`;

    const hiddenComments = document.getElementById(`comments-${postId}`);
    if (hiddenComments && hiddenComments.innerHTML.trim() !== "") {
        commentsList.innerHTML = hiddenComments.innerHTML;
    } else {
        commentsList.innerHTML = '<p class="no-comments-msg text-xs text-stone-500 text-center py-4">No comments yet.</p>';
    }

    if (modal) modal.classList.remove('hidden');
}

function closeCommentModal() {
    const modal = document.getElementById('commentModal');
    if (modal) modal.classList.add('hidden');
    activePostId = null;
}

// Global Keyboard Shortcut: ESC key closes modals
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeCommentModal();
        closeLogoutModal();
        closeCreatePostModal();
    }
});

/* ==========================================================================
   GLOBAL FORM DELEGATION (AJAX COMMENTS & LIKES)
   ========================================================================== */

document.addEventListener('submit', async function (e) {
    
    // --- 1. COMMENT FORM SUBMISSION ---
    if (e.target && e.target.id === 'modalCommentForm') {
        e.preventDefault();

        const form = e.target;
        if (!activePostId) return;

        const targetUrl = `/comment-post/${activePostId}/`;
        const formData = new FormData(form);
        const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');

        try {
            const response = await fetch(targetUrl, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                // Clear input field
                form.reset();

                // Clear placeholder text if first comment
                const commentsList = document.getElementById('modalCommentsList');
                const noCommentsMsg = commentsList?.querySelector('.no-comments-msg');
                if (noCommentsMsg) noCommentsMsg.remove();

                // Construct new comment HTML string
                const commentHtml = `
                    <div class="bg-stone-800 rounded-xl p-3 mb-2">
                        <p class="text-xs font-bold text-emerald-400">${escapeHtml(data.author)}</p>
                        <p class="text-sm text-stone-300 mt-0.5">${escapeHtml(data.content)}</p>
                    </div>
                `;

                // Render comment into modal scroll list and auto-scroll down
                if (commentsList) {
                    commentsList.insertAdjacentHTML('beforeend', commentHtml);
                    commentsList.scrollTop = commentsList.scrollHeight;
                }

                // Synchronize hidden comments list in main feed card
                const hiddenComments = document.getElementById(`comments-${activePostId}`);
                if (hiddenComments) {
                    const emptyHiddenMsg = hiddenComments.querySelector('.text-stone-500');
                    if (emptyHiddenMsg) emptyHiddenMsg.remove();
                    hiddenComments.insertAdjacentHTML('beforeend', commentHtml);
                }

                // Update total comment counters across post feed
                const countElements = document.querySelectorAll(`.comment-count[data-post-id="${activePostId}"]`);
                countElements.forEach(el => {
                    el.textContent = data.comments_count;
                });
            } else {
                alert(data.error || "Failed to post comment.");
            }
        } catch (err) {
            console.error("Comment submit error:", err);
        }
    }

    // --- 2. LIKE BUTTON FORM SUBMISSION ---
    if (e.target && e.target.classList.contains('like-form')) {
        e.preventDefault();

        const form = e.target;
        const postId = form.dataset.postId;
        const csrfInput = form.querySelector('[name=csrfmiddlewaretoken]');
        const csrfToken = csrfInput ? csrfInput.value : getCookie('csrftoken');

        try {
            const response = await fetch(`/like-post/${postId}/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                }
            });
            
            const data = await response.json();

            // Update like counter text
            const countSpan = form.querySelector('.like-count');
            if (countSpan) countSpan.textContent = data.likes_count;

            // Toggle active visual states on heart icon
            const svg = form.querySelector('.like-svg');
            if (svg) {
                if (data.liked) {
                    svg.classList.add('text-rose-500', 'fill-rose-500');
                    svg.classList.remove('text-stone-400', 'fill-none');
                    if (countSpan) {
                        countSpan.classList.add('text-rose-400');
                        countSpan.classList.remove('text-stone-300');
                    }
                } else {
                    svg.classList.remove('text-rose-500', 'fill-rose-500');
                    svg.classList.add('text-stone-400', 'fill-none');
                    if (countSpan) {
                        countSpan.classList.remove('text-rose-400');
                        countSpan.classList.add('text-stone-300');
                    }
                }
            }
        } catch (err) {
            console.error("Like toggle error:", err);
        }
    }
});

/* ==========================================================================
   NOTIFICATION DROPDOWN TOGGLE
   ========================================================================== */

function toggleNotifications() {
    const dropdown = document.getElementById('notificationDropdown');
    if (dropdown) dropdown.classList.toggle('hidden');

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');

    fetch('/notifications/read/', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        const badge = document.getElementById('notification-badge');
        if (badge) badge.remove();
    })
    .catch(err => console.error("Notifications error:", err));
}



/* ==========================================================================
   SIDE BAR / NOTIFICATION
   ========================================================================== */
function toggleSidebar() {
        const sidebar = document.getElementById("sidebarPanel");
        const backdrop = document.getElementById("sidebarBackdrop");
        
        sidebar.classList.toggle("-translate-x-full");
        backdrop.classList.toggle("hidden");
    }

    async function toggleNotifications() {
        const dropdown = document.getElementById("notificationDropdown");
        const badge = document.getElementById("notification-badge");
        
        dropdown.classList.toggle("hidden");

        // When opening the dropdown, clear the unread badge and mark notifications read in the backend
        if (!dropdown.classList.contains("hidden") && badge) {
            badge.remove();
            try {
                await fetch("/notifications/read/", {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
            } catch (err) {
                console.error("Error marking notifications read:", err);
            }
        }
    }

    // Close notifications dropdown when clicking outside
    document.addEventListener("click", function(event) {
        const dropdown = document.getElementById("notificationDropdown");
        const bellButton = event.target.closest("button[onclick='toggleNotifications()']");
        
        if (!bellButton && dropdown && !dropdown.contains(event.target)) {
            dropdown.classList.add("hidden");
        }
    });

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }