// popup.js —— Cairn 插件弹窗逻辑(Day 11:登录 + 真实保存)

const API_BASE = 'http://localhost:8000';

// 入口:页面加载完
document.addEventListener('DOMContentLoaded', async () => {
    const token = await getToken();
    
    if (token) {
        await renderSaveView();
    } else {
        renderLoginView();
    }
});


// ===== 视图切换 =====

function renderLoginView() {
    document.getElementById('login-view').classList.remove('hidden');
    document.getElementById('save-view').classList.add('hidden');

    document.getElementById('open-web-btn').addEventListener('click', () => {
        chrome.tabs.create({ url: 'http://localhost:3000/login' });
        window.close();
    });
    document.getElementById('login-btn').addEventListener('click', handleLogin);
    document.getElementById('email').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') document.getElementById('password').focus();
    });
    document.getElementById('password').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleLogin();
    });
}


async function renderSaveView() {
    document.getElementById('login-view').classList.add('hidden');
    document.getElementById('save-view').classList.remove('hidden');
    
    // 显示当前页面
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    document.getElementById('page-title').textContent = tab.title || 'Untitled';
    document.getElementById('page-url').textContent = tab.url || '';
    
    document.getElementById('save-btn').addEventListener('click', () => handleSave(tab));
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
}


// ===== 登录逻辑 =====

async function handleLogin() {
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
        // OAuth2 Password Flow 用 form-data 传参
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);
        
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData,
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Login failed');
        }
        
        const data = await response.json();
        await saveToken(data.access_token);
        
        // 切换到保存视图
        await renderSaveView();
    } catch (error) {
        statusEl.textContent = `❌ ${error.message}`;
        statusEl.className = 'status error';
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
}


async function handleLogout() {
    await chrome.storage.local.remove('cairn_token');
    renderLoginView();
}


// ===== 保存文章逻辑 =====

async function handleSave(tab) {
    const saveBtn = document.getElementById('save-btn');
    const statusEl = document.getElementById('status');
    
    saveBtn.disabled = true;
    saveBtn.textContent = 'Extracting...';
    statusEl.textContent = '';
    statusEl.className = 'status';
    
    try {
        // 1. 抓取内容(沿用 Day 9 逻辑)
        const article = await extractArticleFromTab(tab);
        
        if (!article.success) {
            throw new Error(article.error);
        }
        
        // 2. 发送到后端
        saveBtn.textContent = 'Saving to Cairn...';
        const result = await sendToBackend(article.data);
        
        // 3. 显示结果
        if (result.is_new) {
            statusEl.textContent = `✅ Saved! AI analysis running in background...`;
            statusEl.className = 'status success';
        } else {
            statusEl.textContent = `ℹ️ Already in your library`;
            statusEl.className = 'status success';
        }
        
        console.log('Cairn saved:', result);
    } catch (error) {
        statusEl.textContent = `❌ ${error.message}`;
        statusEl.className = 'status error';
        console.error('Cairn error:', error);
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save This Page';
    }
}


async function sendToBackend(articleData) {
    const token = await getToken();
    if (!token) throw new Error('Please sign in first');
    
    const response = await fetch(`${API_BASE}/api/articles`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
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
    
    if (response.status === 401) {
        await chrome.storage.local.remove('cairn_token');
        throw new Error('Session expired, please sign in again');
    }
    
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Save failed');
    }
    
    return await response.json();
}


// ===== 抓取(沿用 Day 9)=====

async function extractArticleFromTab(tab) {
    await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['lib/Readability.js'],
    });
    
    await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content.js'],
    });
    
    return await chrome.tabs.sendMessage(tab.id, { action: 'extract' });
}


// ===== Token 存储 =====

const WEB_APP_ORIGINS = [
    'http://localhost:3000',
];

async function getToken() {
    // 1. 先查扩展自己的 storage
    const data = await chrome.storage.local.get('cairn_token');
    if (data.cairn_token) return data.cairn_token;

    // 2. 尝试从已打开的网页端读取 localStorage token
    const token = await readTokenFromWebApp();
    if (token) {
        await chrome.storage.local.set({ cairn_token: token });
        return token;
    }

    return null;
}

async function readTokenFromWebApp() {
    for (const origin of WEB_APP_ORIGINS) {
        const tabs = await chrome.tabs.query({ url: `${origin}/*` });
        if (tabs.length === 0) continue;
        try {
            const results = await chrome.scripting.executeScript({
                target: { tabId: tabs[0].id },
                func: () => localStorage.getItem('cairn_token'),
            });
            const token = results?.[0]?.result;
            if (token) return token;
        } catch {
            // tab 不可注入，跳过
        }
    }
    return null;
}

async function saveToken(token) {
    await chrome.storage.local.set({ cairn_token: token });
}