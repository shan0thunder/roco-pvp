/**
 * 洛克王国世界PVP助手 — 启动入口
 */
document.addEventListener('DOMContentLoaded', async () => {
  // 深色模式
  const themeKey = 'pvp_theme';
  const savedTheme = localStorage.getItem(themeKey);
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = savedTheme || (prefersDark ? 'dark' : 'light');
  if (theme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.textContent = theme === 'dark' ? '浅色' : '深色';
    themeToggle.addEventListener('click', (e) => {
      e.preventDefault();
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem(themeKey, 'light');
        themeToggle.textContent = '深色';
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem(themeKey, 'dark');
        themeToggle.textContent = '浅色';
      }
    });
  }

  // 初始化
  Renderer.init();
  Router.init();
  Router.onChange(() => Renderer._renderCurrentView());
  Renderer._renderCurrentView();

  // 显示版本
  try {
    const data = await DataStore.load();
    const versionEl = document.getElementById('dataVersion');
    if (versionEl && data._meta?.exported_at) {
      versionEl.textContent = data._meta.exported_at.slice(0, 10);
    }
  } catch (e) {
    document.getElementById('mainContent').innerHTML =
      '<div class="empty-state">⚠️ 数据文件未找到<br>请先运行: <code>python cli.py export-product</code></div>';
  }
});
