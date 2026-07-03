#!/usr/bin/env python3
with open('d:/桌面/目录/洛克PVP/frontend/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

old = "html += '<div class=\"page-header\"><h2>属性克制表</h2><p>攻击\\防守 · 2=克制 0.5=被抗 1=普通</p></div>';"
new = "html += '<div class=\"page-header\"><h2>属性克制表</h2><p>攻击\\防守 · 2=克制 0.5=被抗 1=普通</p></div>';\n    html += '<div style=\"font-size:11px;color:var(--neutral-500);margin-bottom:12px\">数据来源：社区整理 · 待游戏内实测验证</div>';"

c = c.replace(old, new)

with open('d:/桌面/目录/洛克PVP/frontend/app.js', 'w', encoding='utf-8') as f:
    f.write(c)
print('Added source note')
