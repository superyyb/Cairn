// popup.js —— Magpie 插件弹窗逻辑

document.addEventListener('DOMContentLoaded', async () => {
    // 1. 获取当前活动标签页
    const [tab] = await chrome.tabs.query({ 
        active: true, 
        currentWindow: true 
    });
    
    // 2. 显示当前页面的标题和 URL
    document.getElementById('page-title').textContent = tab.title || 'Untitled';
    document.getElementById('page-url').textContent = tab.url || '';
    
    // 3. 绑定 Save 按钮
    const saveBtn = document.getElementById('save-btn');
    const statusEl = document.getElementById('status');
    
    saveBtn.addEventListener('click', async () => {
        saveBtn.disabled = true;
        saveBtn.textContent = 'Extracting...';
        statusEl.textContent = '';
        statusEl.className = 'status';
        
        try {
            // 调用抓取
            const article = await extractArticleFromTab(tab);
            
            if (!article.success) {
                throw new Error(article.error);
            }
            
            // 显示成功信息
            const { title, length, siteName } = article.data;
            statusEl.textContent = `✅ Captured ${length} chars from "${siteName || 'this page'}"`;
            statusEl.className = 'status success';
            
            // 打印完整抓取结果到 console,方便调试
            console.log('Magpie extracted:', article.data);
            
        } catch (error) {
            statusEl.textContent = `❌ ${error.message}`;
            statusEl.className = 'status error';
            console.error('Magpie error:', error);
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save This Page';
        }
    });
});


/**
 * 向 content script 发消息,触发正文抓取。
 * 先注入 Readability.js 和 content.js,然后发消息。
 */
async function extractArticleFromTab(tab) {
    // 1. 注入 Readability.js 库到目标页面
    await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['lib/Readability.js'],
    });
    
    // 2. 注入我们的 content.js(定义了 extractArticle 函数和消息监听)
    await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content.js'],
    });
    
    // 3. 发消息让 content script 执行抓取
    const response = await chrome.tabs.sendMessage(tab.id, {
        action: 'extract',
    });
    
    return response;
}