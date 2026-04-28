// content.js —— 注入到用户网页里,负责抓取正文

/**
 * 使用 Mozilla Readability 提取网页的干净正文。
 * 这个函数会在点击保存时被调用。
 */
function extractArticle() {
    try {
        // 1. 克隆 document,避免修改用户正在看的页面
        const documentClone = document.cloneNode(true);
        
        // 2. 用 Readability 解析
        const reader = new Readability(documentClone);
        const article = reader.parse();
        
        // 3. 如果 Readability 解析失败,返回 null
        if (!article) {
            return {
                success: false,
                error: 'Unable to extract article. This page may not have readable content.',
            };
        }
        
        // 4. 返回抓取结果
        return {
            success: true,
            data: {
                url: window.location.href,
                title: article.title,
                byline: article.byline,           // 作者
                excerpt: article.excerpt,          // 短摘要
                content: article.textContent,      // 纯文本正文
                contentHtml: article.content,      // HTML 格式正文
                siteName: article.siteName,        // 网站名
                lang: article.lang,                // 语言
                length: article.length,            // 字符数
                publishedTime: article.publishedTime,
            }
        };
    } catch (error) {
        return {
            success: false,
            error: error.message,
        };
    }
}

// 把 extractArticle 暴露给 popup 调用
// 通过 message passing 机制,popup 发消息来触发
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'extract') {
        const result = extractArticle();
        sendResponse(result);
        return true; // 告诉 Chrome 我们异步返回了
    }
});