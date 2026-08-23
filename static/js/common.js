/* MC-Server-Hub 公用脚本：API 封装 / Toast / 主题 / 复制 / 转义 */

async function api(url, options = {}) {
    try {
        const resp = await fetch(url, options);
        if (!resp.ok) return null;
        return await resp.json();
    } catch (e) { console.error('API error:', url, e); return null; }
}

function showToast(msg, isError = false) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `fixed bottom-6 right-6 px-5 py-3 rounded-lg shadow-lg text-white z-[100] fade-in ${isError ? 'bg-red-500' : 'bg-gray-800'}`;
    setTimeout(() => t.classList.add('hidden'), 2500);
}

function toggleTheme() {
    document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
}

function copyText(text) {
    // 创建一个隐藏的文本框
    const ta = document.createElement('textarea');
    ta.value = text;
    // 关键：必须脱离文档流且不可见，防止页面闪烁
    ta.style.cssText = 'position:fixed; left:-9999px; top:-9999px; opacity:0;';
    document.body.appendChild(ta);

    // 兼容移动端和桌面端
    ta.focus();
    ta.select();
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showToast('已复制: ' + text);
        } else {
            showToast('复制失败，请手动复制', true);
        }
    } catch (err) {
        showToast('浏览器不支持自动复制', true);
    }
    // 清理 DOM
    document.body.removeChild(ta);
}

function esc(s) { if (s == null) return ''; return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }

// 主题初始化（跟随本地设置或系统偏好）
if (localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
}
