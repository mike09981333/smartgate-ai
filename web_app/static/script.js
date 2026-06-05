const video = document.getElementById('videoElement');
const canvas = document.getElementById('canvasElement');
const notif = document.getElementById('notification');
const loading = document.getElementById('loading');
const usersGrid = document.getElementById('users-grid');
const userCount = document.getElementById('user-count');
const historyList = document.getElementById('history-list');
const historyCount = document.getElementById('history-count');

async function startWebcam() {
    if (!video) return;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } }
        });
        video.srcObject = stream;
    } catch (err) {
        showNotification("Impossible d'accéder à la caméra.", "error");
        console.error(err);
    }
}

function switchTab(tab) {
    const registerSection = document.getElementById('register-section');
    const verifySection = document.getElementById('verify-section');
    const registerTab = document.getElementById('tab-register');
    const verifyTab = document.getElementById('tab-verify');

    if (!registerSection || !verifySection || !registerTab || !verifyTab) return;

    registerTab.classList.toggle('active', tab === 'register');
    verifyTab.classList.toggle('active', tab === 'verify');
    registerSection.style.display = tab === 'register' ? 'block' : 'none';
    verifySection.style.display = tab === 'verify' ? 'block' : 'none';

    if (notif) {
        notif.style.display = 'none';
    }
}

async function captureAndSend(action) {
    if (!video || !canvas || !video.srcObject) return;

    if (action === 'register') {
        const nameInput = document.getElementById('username');
        const name = nameInput ? nameInput.value.trim() : '';
        if (!name) {
            showNotification("Veuillez entrer un nom avant de vous enregistrer.", "error");
            if (nameInput) nameInput.focus();
            return;
        }
    }

    if (notif) {
        notif.style.display = 'none';
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const isVerify = action === 'verify';

    if (isVerify) {
        const frozenFrame = document.getElementById('frozenFrame');
        const scanOverlay = document.getElementById('scanOverlay');

        if (frozenFrame && scanOverlay) {
            frozenFrame.width = video.videoWidth;
            frozenFrame.height = video.videoHeight;
            const frozenCtx = frozenFrame.getContext('2d');
            frozenCtx.drawImage(video, 0, 0, frozenFrame.width, frozenFrame.height);
            frozenFrame.style.display = 'block';
            scanOverlay.style.display = 'block';
        }
    } else if (loading) {
        loading.style.display = 'flex';
    }

    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);

    try {
        const endpoint = action === 'register' ? '/register' : '/verify';
        const body = action === 'register'
            ? JSON.stringify({ image: dataUrl, name: document.getElementById('username').value.trim() })
            : JSON.stringify({ image: dataUrl });

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body
        });

        const result = await response.json();

        if (response.ok) {
            if (action === 'register') {
                showNotification(result.message, "success");
                document.getElementById('username').value = '';
                fetchUsers();
            } else {
                showNotification(result.message, result.status === 'success' ? "success" : "error");
                fetchAccessLogs();
            }
        } else {
            showNotification(result.message, "error");
            if (action === 'verify') {
                fetchAccessLogs();
            }
        }
    } catch (err) {
        showNotification("Erreur de connexion au serveur.", "error");
        console.error(err);
    } finally {
        if (isVerify) {
            setTimeout(() => {
                const frozenFrame = document.getElementById('frozenFrame');
                const scanOverlay = document.getElementById('scanOverlay');
                if (frozenFrame) frozenFrame.style.display = 'none';
                if (scanOverlay) scanOverlay.style.display = 'none';
            }, 800);
        } else if (loading) {
            loading.style.display = 'none';
        }
    }
}

function showNotification(msg, type) {
    if (!notif) return;

    const icon = notif.querySelector('.notif-icon');
    const text = notif.querySelector('.notif-text');

    if (text) {
        text.textContent = msg;
    }
    notif.className = `notification notif-${type}`;
    notif.style.display = 'flex';

    if (icon) {
        icon.setAttribute('data-lucide', type === 'success' ? 'check-circle' : 'alert-circle');
    }
    lucide.createIcons();
}

async function fetchUsers() {
    if (!usersGrid || !userCount) return;

    try {
        const response = await fetch('/users');
        const data = await response.json();
        renderUsers(data.users || []);
    } catch (err) {
        console.error('Erreur lors du chargement des utilisateurs:', err);
    }
}

function renderUsers(users) {
    if (!usersGrid || !userCount) return;

    userCount.textContent = users.length;
    usersGrid.innerHTML = '';

    if (users.length === 0) {
        usersGrid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon-wrapper">
                    <i data-lucide="lock" class="empty-icon"></i>
                </div>
                <p class="empty-title">Aucune personne enregistrée</p>
                <p class="empty-hint">Utilisez la page Accueil pour ajouter des personnes.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    users.forEach((user, index) => {
        const card = document.createElement('article');
        card.className = 'user-card';
        card.style.animationDelay = `${index * 0.08}s`;

        const media = document.createElement('div');
        media.className = 'user-media';

        const photo = document.createElement('img');
        photo.className = 'user-photo';
        photo.src = user.photo_url;
        photo.alt = `Photo de ${user.name}`;

        media.appendChild(photo);

        const body = document.createElement('div');
        body.className = 'user-card-body';

        const heading = document.createElement('div');
        heading.className = 'user-card-heading';

        const name = document.createElement('h3');
        name.className = 'user-name';
        name.textContent = user.name;

        const badge = document.createElement('span');
        badge.className = 'user-badge';
        badge.innerHTML = '<i data-lucide="shield-check"></i>Autorisé';

        heading.append(name, badge);

        const meta = document.createElement('div');
        meta.className = 'user-meta';
        meta.innerHTML = '<i data-lucide="badge-check"></i><span>Profil biométrique enregistré</span>';

        const footer = document.createElement('div');
        footer.className = 'user-card-footer';
        footer.innerHTML = '<i data-lucide="scan-face"></i><span>Prêt pour le contrôle d\'accès</span>';

        body.append(heading, meta, footer);

        const actions = document.createElement('div');
        actions.className = 'user-card-actions';

        const deleteButton = document.createElement('button');
        deleteButton.className = 'delete-user-btn';
        deleteButton.type = 'button';
        deleteButton.title = `Supprimer ${user.name}`;
        deleteButton.setAttribute('aria-label', `Supprimer ${user.name}`);
        deleteButton.innerHTML = '<i data-lucide="trash-2"></i><span>Supprimer</span>';
        deleteButton.addEventListener('click', () => deleteUser(user.name));

        actions.appendChild(deleteButton);
        card.append(media, body, actions);
        usersGrid.appendChild(card);
    });

    lucide.createIcons();
}

async function fetchAccessLogs() {
    if (!historyList || !historyCount) return;

    try {
        const response = await fetch('/access-logs?limit=12');
        const data = await response.json();
        renderAccessLogs(data.logs || []);
    } catch (err) {
        console.error("Erreur lors du chargement de l'historique:", err);
    }
}

function renderAccessLogs(logs) {
    if (!historyList || !historyCount) return;

    historyCount.textContent = logs.length;
    historyList.innerHTML = '';

    if (logs.length === 0) {
        historyList.innerHTML = `
            <div class="empty-state history-empty-state">
                <div class="empty-icon-wrapper">
                    <i data-lucide="file-clock" class="empty-icon"></i>
                </div>
                <p class="empty-title">Aucun passage enregistré</p>
                <p class="empty-hint">Les accès accordés et refusés apparaîtront ici.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    logs.forEach((log, index) => {
        const item = document.createElement('div');
        item.className = `history-item history-${log.status}`;
        item.style.animationDelay = `${index * 0.05}s`;

        const iconName = log.status === 'accorde' ? 'badge-check' : 'shield-x';
        const statusLabel = log.status === 'accorde' ? 'Accès accordé' : 'Accès refusé';
        const isUnauthorizedFace = !log.person_name || log.person_name === 'Inconnu';
        const personName = isUnauthorizedFace ? 'Visage non autorisé' : log.person_name;
        const similarity = typeof log.similarity === 'number'
            ? `${Math.round(log.similarity * 100)}%`
            : '--';
        const barrierLabel = log.barrier_opened ? 'Barrière ouverte' : 'Barrière fermée';

        item.innerHTML = `
            <div class="history-icon-wrap">
                <i data-lucide="${iconName}" class="history-icon"></i>
            </div>
            <div class="history-content">
                <div class="history-top-row">
                    <span class="history-name">${personName}</span>
                    <span class="history-status-pill">${statusLabel}</span>
                </div>
                <div class="history-meta">
                    <span><i data-lucide="calendar-days"></i>${log.access_date}</span>
                    <span><i data-lucide="clock-3"></i>${log.access_time}</span>
                    <span><i data-lucide="sun-medium"></i>${log.access_day}</span>
                </div>
                <div class="history-bottom-row">
                    <span class="history-score">Similarité: ${similarity}</span>
                    <span class="history-barrier">${barrierLabel}</span>
                </div>
            </div>
        `;

        historyList.appendChild(item);
    });

    lucide.createIcons();
}

async function deleteUser(name) {
    if (!confirm(`Supprimer ${name} ?`)) return;

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

window.addEventListener('load', () => {
    startWebcam();
    fetchUsers();
    fetchAccessLogs();
    lucide.createIcons();
});
