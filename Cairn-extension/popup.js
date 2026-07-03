const API_BASE = 'http://localhost:8000';
const GOOGLE_CLIENT_ID = '319929818622-9b0ud4lju4kt9h3e495nleaa9p1u4c6k.apps.googleusercontent.com';

// ===== 入口 =====

document.addEventListener('DOMContentLoaded', async () => {
    const token = await getAccessToken();
    if (token) {
        await renderSaveView();
    } else {
        renderLoginView();
    }
});


// ===== Token 存储 =====
// access token → chrome.storage.session（关闭浏览器自动清除）
// refresh token → chrome.storage.local（持久化，用于重新获取 access token）

async function getAccessToken() {
    const data = await chrome.storage.session.get('access_token');
    return data.access_token || null;
}

async function getRefreshToken() {
    const data = await chrome.storage.local.get('refresh_token');
    return data.refresh_token || null;
}

async function saveTokens(accessToken, refreshToken) {
    await chrome.storage.session.set({ access_token: accessToken });
    if (refreshToken) {
        await chrome.storage.local.set({ refresh_token: refreshToken });
    }
}

async function clearTokens() {
    await chrome.storage.session.remove('access_token');
    await chrome.storage.local.remove('refresh_token');
}


// ===== Token 自动刷新 =====

async function refreshAccessToken() {
    const refreshToken = await getRefreshToken();
    if (!refreshToken) return null;

    try {
        const res = await fetch(`${API_BASE}/api/auth/refresh?client_type=extension`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!res.ok) {
            await clearTokens();
            return null;
        }

        const data = await res.json();
        await saveTokens(data.access_token, data.refresh_token);
        return data.access_token;
    } catch {
        return null;
    }
}

async function authFetch(path, options = {}, _retry = true) {
    const token = await getAccessToken();

    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...options.headers,
        },
    });

    if (res.status === 401 && _retry) {
        const newToken = await refreshAccessToken();
        if (newToken) return authFetch(path, options, false);
        await clearTokens();
        renderLoginView();
        throw new Error('Session expired, please sign in again');
    }

    return res;
}


// ===== 视图切换 =====

function renderLoginView() {
    document.getElementById('login-view').classList.remove('hidden');
    document.getElementById('save-view').classList.add('hidden');

    document.getElementById('google-btn').addEventListener('click', handleGoogleLogin);
    document.getElementById('login-btn').addEventListener('click', handleEmailLogin);
    document.getElementById('email').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') document.getElementById('password').focus();
    });
    document.getElementById('password').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleEmailLogin();
    });
}

async function renderSaveView() {
    document.getElementById('login-view').classList.add('hidden');
    document.getElementById('save-view').classList.remove('hidden');

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    document.getElementById('page-title').textContent = tab.title || 'Untitled';
    document.getElementById('page-url').textContent = tab.url || '';

    document.getElementById('save-btn').addEventListener('click', () => handleSave(tab));
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
}


// ===== Google OAuth =====

async function handleGoogleLogin() {
    const btn = document.getElementById('google-btn');
    const statusEl = document.getElementById('login-status');
    btn.disabled = true;
    statusEl.textContent = '';

    try {
        const redirectUrl = chrome.identity.getRedirectURL();
        const nonce = Array.from(crypto.getRandomValues(new Uint8Array(16)))
            .map(b => b.toString(16).padStart(2, '0')).join('');

        const params = new URLSearchParams({
            client_id: GOOGLE_CLIENT_ID,
            response_type: 'id_token',
            redirect_uri: redirectUrl,
            scope: 'openid email profile',
            nonce,
        });

        let responseUrl;
        try {
            responseUrl = await chrome.identity.launchWebAuthFlow({
                url: `https://accounts.google.com/o/oauth2/auth?${params}`,
                interactive: true,
            });
        } catch {
            throw new Error('Google sign-in was cancelled');
        }

        const hashParams = new URLSearchParams(new URL(responseUrl).hash.slice(1));
        const idToken = hashParams.get('id_token');
        if (!idToken) throw new Error('No id_token received from Google');

        const res = await fetch(`${API_BASE}/api/auth/google?client_type=extension`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential: idToken }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Google sign-in failed');
        }

        const data = await res.json();
        await saveTokens(data.access_token, data.refresh_token);
        await renderSaveView();
    } catch (error) {
        statusEl.textContent = `❌ ${error.message}`;
        statusEl.className = 'status error';
        btn.disabled = false;
    }
}


// ===== 邮箱密码登录 =====

async function handleEmailLogin() {
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const statusEl = document.getElementById('login-status');
    const btn = document.getElementById('login-btn');

    if (!email || !password) {
        statusEl.textContent = 'Please fill in both fields';
        statusEl.className = 'status error';
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Signing in...';
    statusEl.textContent = '';

    try {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const res = await fetch(`${API_BASE}/api/auth/login?client_type=extension`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Login failed');
        }

        const data = await res.json();
        await saveTokens(data.access_token, data.refresh_token);
        await renderSaveView();
    } catch (error) {
        statusEl.textContent = `❌ ${error.message}`;
        statusEl.className = 'status error';
        btn.disabled = false;
        btn.textContent = 'Sign In with Email';
    }
}


// ===== 退出登录 =====

async function handleLogout() {
    const refreshToken = await getRefreshToken();
    if (refreshToken) {
        await fetch(`${API_BASE}/api/auth/logout?client_type=extension`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
        }).catch(() => {});
    }
    await clearTokens();
    renderLoginView();
}


// ===== 保存文章 =====

async function handleSave(tab) {
    const saveBtn = document.getElementById('save-btn');
    const statusEl = document.getElementById('status');

    saveBtn.disabled = true;
    saveBtn.textContent = 'Extracting...';
    statusEl.textContent = '';
    statusEl.className = 'status';

    try {
        const article = await extractArticleFromTab(tab);
        if (!article.success) throw new Error(article.error);

        saveBtn.textContent = 'Saving to Cairn...';
        const result = await sendToBackend(article.data);

        if (result.is_new) {
            statusEl.textContent = `✅ Saved! AI analysis running in background...`;
        } else {
            statusEl.textContent = `ℹ️ Already in your library`;
        }
        statusEl.className = 'status success';
    } catch (error) {
        statusEl.textContent = `❌ ${error.message}`;
        statusEl.className = 'status error';
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save This Page';
    }
}

async function sendToBackend(articleData) {
    const res = await authFetch('/api/articles', {
        method: 'POST',
        body: JSON.stringify({
            url: articleData.url,
            title: articleData.title,
            content: articleData.content,
            excerpt: articleData.excerpt,
            byline: articleData.byline,
            site_name: articleData.siteName,
            lang: articleData.lang,
            length: articleData.length,
        }),
    });

    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Save failed');
    }

    return res.json();
}


// ===== 抓取文章内容 =====

async function extractArticleFromTab(tab) {
    await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['lib/Readability.js'],
    });
    await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content.js'],
    });
    return chrome.tabs.sendMessage(tab.id, { action: 'extract' });
}
