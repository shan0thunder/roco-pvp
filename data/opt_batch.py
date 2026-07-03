#!/usr/bin/env python3
"""Batch apply optimizations 2-9"""

# ====== app.js changes ======
with open('d:/桌面/目录/洛克PVP/frontend/app.js', 'r', encoding='utf-8') as f:
    app = f.read()

# P0-3: Speed sort toggle button in filter row
old_petsort_btn = "+ '<button class=\"btn-filter' + (this._petFilterElem === '' && this._petFilterFunc === '' && !this._petFilterLeader ? ' active' : '') + '\" onclick=\"Renderer._petFilterElem=\\'\\';Renderer._petFilterFunc=\\'\\';Renderer._petFilterLeader=false;Renderer._renderCurrentView()\">全部</button>'"
new_petsort_btn = old_petsort_btn + "\n      + '<button class=\"btn-filter\" onclick=\"Renderer._petSortBy=Renderer._petSortBy===\\'speed\\'?null:\\'speed\\';Renderer._renderCurrentView()\">' + (this._petSortBy === 'speed' ? '\\u2713 按速' : '\\u23F3 速度') + '</button>'"
if old_petsort_btn in app:
    app = app.replace(old_petsort_btn, new_petsort_btn)
    print("P0-3: Speed sort button added")
else:
    print("P0-3: Speed sort button pattern not found")

# P2-8: Type chart - add row/column highlighting on hover
old_type_chart = "html += '<div class=\"type-chart-table\"><thead><tr><th>攻\\\\守</th>';"
# Add data attributes for hover highlighting
new_type_chart = "html += '<div class=\"type-chart-table\" id=\"typeChartTable\"><thead><tr><th>攻\\\\守</th>';"
app = app.replace(old_type_chart, new_type_chart)

# Add hover script for type chart - highlight row and column
old_type_end = "this._container.innerHTML = html;\n  },"
new_type_end = """this._container.innerHTML = html;
    // 高亮行列
    const tbl = document.getElementById('typeChartTable');
    if (tbl) {
      tbl.querySelectorAll('td').forEach(cell => {
        cell.addEventListener('mouseenter', function() {
          const row = this.parentElement;
          const idx = Array.from(row.children).indexOf(this);
          row.querySelectorAll('td').forEach(c => c.style.opacity = '1');
          tbl.querySelectorAll('tr').forEach(r => {
            const td = r.children[idx];
            if (td) td.style.opacity = '1';
          });
        });
        cell.addEventListener('mouseleave', function() {
          tbl.querySelectorAll('td').forEach(c => c.style.opacity = ''));
        });
      });
    }
  },"""
app = app.replace(old_type_end, new_type_end)

# P2-9: Responsive - already exists in CSS, but add better mobile handling
# P1-4: Add right-click context menu to editor cards (in editor.js)

with open('d:/桌面/目录/洛克PVP/frontend/app.js', 'w', encoding='utf-8') as f:
    f.write(app)

# ====== editor.js changes ======
with open('d:/桌面/目录/洛克PVP/editor/editor.js', 'r', encoding='utf-8') as f:
    ed = f.read()

# P0-2: Data validator function
old_esc = "  _esc(str) {"
new_validator = """  checkData() {
    const pets = this._data?.pets || [];
    let issues = [];
    // 检查重复精灵名
    const names = pets.map(p => p.name);
    const dupes = names.filter((n,i) => names.indexOf(n) !== i);
    if (dupes.length) issues.push('\\u91CD\\u590D\\u7CBE\\u7075\\u540D\\uFF1A' + [...new Set(dupes)].join(', '));
    // 检查种族值异常
    for (const p of pets) {
      const st = p.stats || {};
      if (st.total && st.total > 900) issues.push(p.name + ' \\u79CD\\u65CF\\u503C\\u8FC7\\u9AD8\\uFF1A' + st.total);
      if (st.total && st.total < 100) issues.push(p.name + ' \\u79CD\\u65CF\\u503C\\u8FC7\\u4F4E\\uFF1A' + st.total);
    }
    // 检查无技能的精灵
    for (const p of pets) {
      if (!p.skills || !p.skills.length) issues.push(p.name + ' \\u65E0\\u6280\\u80FD');
    }
    // 检查无图片
    for (const p of pets) {
      if (!p.image) issues.push(p.name + ' \\u65E0\\u56FE\\u7247');
    }
    let html = '<div class=\"page-header\"><h2>\\u6570\\u636E\\u5065\\u5EB7\\u68C0\\u67E5</h2></div>';
    if (!issues.length) {
      html += '<div style=\"padding:40px;text-align:center;color:var(--success-500);font-size:16px\">\\u2705 \\u6570\\u636E\\u5065\\u5EB7\\uFF0C\\u65E0\\u5F02\\u5E38</div>';
    } else {
      html += '<div style=\"margin-bottom:12px\">\\u53D1\\u73B0 ' + issues.length + ' \\u4E2A\\u95EE\\u9898\\uFF1A</div>';
      for (const issue of issues) {
        html += '<div style=\"padding:6px 12px;margin:4px 0;background:var(--danger-50);border-radius:6px;font-size:13px\">' + this._esc(issue) + '</div>';
      }
    }
    html += '<div style=\"margin-top:16px\"><button class=\"btn\" onclick=\"Editor.render()\">\\u8FD4\\u56DE</button></div>';
    this._container.innerHTML = html;
  },

  _esc(str) {"""
ed = ed.replace(old_esc, new_validator)

# P1-4: Add right-click context menu to edit cards
old_card_render = "html += '<div class=\"card edit-card\" onclick=\"Editor.openEdit(\\'" + this._esc(p.name) + "\\')\">'"
# Replace with right-click support
new_card_render = "html += '<div class=\"card edit-card\" onclick=\"Editor.openEdit(\\'" + this._esc(p.name) + "\\')\" oncontextmenu=\"event.preventDefault();Editor.showContextMenu(event,\\'" + this._esc(p.name) + "\\')\">'"
ed = ed.replace(old_card_render, new_card_render)

# Add context menu methods before _esc
old_esc2 = "  _esc(str) {"
new_context = """  showContextMenu(event, name) {
    const menu = document.getElementById('ctxMenu');
    if (menu) menu.remove();
    const div = document.createElement('div');
    div.id = 'ctxMenu';
    div.style.cssText = 'position:fixed;z-index:3000;background:var(--white);border:1px solid var(--neutral-200);border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.12);padding:4px 0;left:' + event.clientX + 'px;top:' + event.clientY + 'px';
    div.innerHTML = '<div style=\"padding:6px 16px;cursor:pointer;font-size:13px\" onmouseover=\"this.style.background=\\'var(--neutral-50)\\'\" onmouseout=\"this.style.background=\\'transparent\\'\" onclick=\"Editor.openEdit(\\'' + this._esc(name) + '\\');document.getElementById(\\'ctxMenu\\').remove()\">\\u270F \\u7F16\\u8F91</div>'
      + '<div style=\"padding:6px 16px;cursor:pointer;font-size:13px\" onmouseover=\"this.style.background=\\'var(--neutral-50)\\'\" onmouseout=\"this.style.background=\\'transparent\\'\" onclick=\"Editor.copyPet(\\'' + this._esc(name) + '\\');document.getElementById(\\'ctxMenu\\').remove()\">\\uD83D\\uDCCB \\u590D\\u5236\\u6570\\u636E</div>'
      + '<div style=\"padding:6px 16px;cursor:pointer;font-size:13px;color:var(--danger-500)\" onmouseover=\"this.style.background=\\'var(--danger-50)\\'\" onmouseout=\"this.style.background=\\'transparent\\'\" onclick=\"if(confirm(\\'\\u786E\\u5B9A\\u5220\\u9664 ' + this._esc(name) + '\\uFF1F\\')){Editor.deletePet(\\'' + this._esc(name) + '\\');document.getElementById(\\'ctxMenu\\').remove()}\">\\uD83D\\uDDD1 \\u5220\\u9664</div>';
    document.body.appendChild(div);
    document.addEventListener('click', function rm() { const m=document.getElementById('ctxMenu'); if(m)m.remove(); document.removeEventListener('click', rm); }, {once:true});
  },

  copyPet(name) {
    const pet = this._data?.pets.find(p => p.name === name);
    if (!pet) return;
    const copy = JSON.parse(JSON.stringify(pet));
    copy.name = name + ' (\\u590D\\u5236)';
    this._data.pets.push(copy);
    this._dirty = true;
    this.render();
    document.getElementById('saveStatus').textContent = '\\u270E \\u5DF2\\u590D\\u5236';
  },

  deletePet(name) {
    this._data.pets = this._data.pets.filter(p => p.name !== name);
    this._dirty = true;
    this.render();
    document.getElementById('saveStatus').textContent = '\\u270E \\u5DF2\\u5220\\u9664';
  },

  _esc(str) {"""
ed = ed.replace(old_esc2, new_context)

with open('d:/桌面/目录/洛克PVP/editor/editor.js', 'w', encoding='utf-8') as f:
    f.write(ed)

# ====== Verify ======
import subprocess
r1 = subprocess.run(['node', '--check', 'd:/桌面/目录/洛克PVP/frontend/app.js'], capture_output=True, text=True)
r2 = subprocess.run(['node', '--check', 'd:/桌面/目录/洛克PVP/editor/editor.js'], capture_output=True, text=True)
print(f'app.js: {"OK" if r1.returncode==0 else r1.stderr[:60]}')
print(f'editor.js: {"OK" if r2.returncode==0 else r2.stderr[:60]}')
