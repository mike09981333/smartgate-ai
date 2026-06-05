const video = document.getElementById('videoElement');
const canvas = document.getElementById('canvasElement');
const notif = document.getElementById('notification');
const loading = document.getElementById('loading');
const usersGrid = document.getElementById('users-grid');
const userCount = document.getElementById('user-count');

// Initialize Webcam
async function startWebcam() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: "user", width: {ideal: 640}, height: {ideal: 480} } 
        });
        video.srcObject = stream;
    } catch (err) {
        showNotification("Impossible d'accéder à la caméra.", "error");
        console.error(err);
    }
}

// Tab Switching logic
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`tab-${tab}`).classList.add('active');

    if (tab === 'register') {
        document.getElementById('register-section').style.display = 'block';
        document.getElementById('verify-section').style.display = 'none';
    } else {
        document.getElementById('register-section').style.display = 'none';
        document.getElementById('verify-section').style.display = 'block';
    }
    notif.style.display = 'none';
}

// Capture Image and Send
async function captureAndSend(action) {
    if (!video.srcObject) return;

    // For registration, require a name
    if (action === 'register') {
        const nameInput = document.getElementById('username');
        const name = nameInput.value.trim();
        if (!name) {
            showNotification("Veuillez entrer un nom avant de vous enregistrer.", "error");
            nameInput.focus();
            return;
        }
    }

    notif.style.display = 'none';

    // Draw video frame to hidden canvas (for sending to API)
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const isVerify = action === 'verify';

    if (isVerify) {
        // Freeze the frame: draw current video to the visible frozen canvas
        const frozenFrame = document.getElementById('frozenFrame');
        const scanOverlay = document.getElementById('scanOverlay');

        frozenFrame.width = video.videoWidth;
        frozenFrame.height = video.videoHeight;
        const frozenCtx = frozenFrame.getContext('2d');
        frozenCtx.drawImage(video, 0, 0, frozenFrame.width, frozenFrame.height);

        // Show frozen frame on top of video + scan animation
        frozenFrame.style.display = 'block';
        scanOverlay.style.display = 'block';
    } else {
        // For register, show simple loading spinner
        loading.style.display = 'flex';
    }

    // Get Base64 image
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);

    try {
        const endpoint = action === 'register' ? '/register' : '/verify';
        let body;

        if (action === 'register') {
            const name = document.getElementById('username').value.trim();
            body = JSON.stringify({ image: dataUrl, name: name });
        } else {
            body = JSON.stringify({ image: dataUrl });
        }

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: body
        });

        const result = await response.json();

        if (response.ok) {
            if (action === 'register') {
                showNotification(result.message, "success");
                document.getElementById('username').value = '';
                fetchUsers();
            } else {
                if (result.status === 'success') {
                    showNotification(result.message, "success");
                } else {
                    showNotification(result.message, "error");
                }
            }
        } else {
            showNotification(result.message, "error");
        }
    } catch (err) {
        showNotification("Erreur de connexion au serveur.", "error");
        console.error(err);
    } finally {
        if (isVerify) {
            // Small delay so user sees the result before unfreezing
            setTimeout(() => {
                document.getElementById('frozenFrame').style.display = 'none';
                document.getElementById('scanOverlay').style.display = 'none';
            }, 800);
        } else {
            loading.style.display = 'none';
        }
    }
}

function showNotification(msg, type) {
    const icon = notif.querySelector('.notif-icon');
    const text = notif.querySelector('.notif-text');

    text.textContent = msg;
    notif.className = `notification notif-${type}`;
    notif.style.display = 'flex';

    // Update icon based on type
    if (type === 'success') {
        icon.setAttribute('data-lucide', 'check-circle');
    } else {
        icon.setAttribute('data-lucide', 'alert-circle');
    }
    lucide.createIcons();
}

// ========== Users Panel ==========

async function fetchUsers() {
    try {
        const response = await fetch('/users');
        const data = await response.json();
        renderUsers(data.users);
    } catch (err) {
        console.error('Erreur lors du chargement des utilisateurs:', err);
    }
}

function renderUsers(users) {
    userCount.textContent = users.length;
    usersGrid.innerHTML = '';

    if (users.length === 0) {
        usersGrid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon-wrapper">
                    <i data-lucide="lock" class="empty-icon"></i>
                </div>
                <p class="empty-title">Aucune personne enregistrée</p>
                <p class="empty-hint">Utilisez l'onglet "S'enregistrer" pour ajouter des personnes.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    users.forEach((user, index) => {
        const card = document.createElement('div');
        card.className = 'user-card';
        card.style.animationDelay = `${index * 0.08}s`;

        const photo = document.createElement('img');
        photo.className = 'user-photo';
        photo.src = user.photo_url;
        photo.alt = `Photo de ${user.name}`;

        const name = document.createElement('div');
        name.className = 'user-name';
        name.textContent = user.name;

        const badge = document.createElement('span');
        badge.className = 'user-badge';
        badge.innerHTML = '<i data-lucide="shield-check"></i>Autorisé';

        const deleteButton = document.createElement('button');
        deleteButton.className = 'delete-user-btn';
        deleteButton.type = 'button';
        deleteButton.title = `Supprimer ${user.name}`;
        deleteButton.setAttribute('aria-label', `Supprimer ${user.name}`);
        deleteButton.innerHTML = '<i data-lucide="trash-2"></i><span>Supprimer</span>';
        deleteButton.addEventListener('click', () => deleteUser(user.name));

        card.append(photo, name, badge, deleteButton);
        usersGrid.appendChild(card);
    });
    lucide.createIcons();
}

async function deleteUser(name) {
    const confirmed = confirm(`Supprimer ${name} ?`);
    if (!confirmed) return;

    try {
        const response = await fetch(`/users/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });
        const result = await response.json();

        if (response.ok) {
            showNotification(result.message, "success");
            fetchUsers();
        } else {
            showNotification(result.message, "error");
        }
    } catch (err) {
        showNotification("Erreur pendant la suppression.", "error");
        console.error(err);
    }
}

// Initialize on page load
window.addEventListener('load', () => {
    startWebcam();
    fetchUsers();
    lucide.createIcons();
});
