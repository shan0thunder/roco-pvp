/**
 * 精灵库编辑器
 * 可修改所有精灵的文字内容和图片
 * 修改后实时同步到主项目
 */

const Editor = {
  _data: null,
  _filterKw: "",
  _filterElem: "",
  _container: null,
  _dirty: false,

  async init() {
    this._container = document.getElementById('mainContent');
    await this.loadData();
    this.render();
  },

  async loadData() {
    try {
      const resp = await fetch('/data/product/product_data.json');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      this._data = await resp.json();
    } catch (e) {
      this._container.innerHTML = '<div class="empty-state">数据加载失败</div>';
      throw e;
    }
  },

  render() {
    const pets = this._data?.pets || [];
    const leaderMap = this._buildLeaderMap();
    let html = '<div class="page-header"><h2>精灵库编辑器</h2><p>共 ' + pets.length + ' 只精灵 · 点击卡片编辑</p></div>';
    // 搜索+筛选
    html += '<div class="builder-filter-bar">'
      + '<input class="builder-search" id="editorSearch" placeholder="搜索精灵名..." value="' + this._esc(this._filterKw) + '" oninput="Editor._filterKw=this.value;Editor.render()">'
      + '<div class="filter-row">'
      + '<button class="btn-filter' + (this._filterElem === '' ? ' active' : '') + '" onclick="Editor._filterElem=\'\';Editor.render()">全部</button>'
      + '<button class="btn-filter' + (this._filterElem === 'leader' ? ' active' : '') + '" onclick="Editor._filterElem=Editor._filterElem===\'leader\'?\'\':\'leader\';Editor.render()">\u{1F451} 首领化</button>'
      + '<select class="filter-select" onchange="Editor._filterElem=this.value;Editor.render()">'
      + '<option value="">系别</option>';
    const ELEMS = ['普通','草','火','水','光','机械','地','冰','龙','电','毒','虫','武','翼','萌','幽','恶','幻'];
    for (const e of ELEMS) {
      html += '<option value="' + e + '"' + (Editor._filterElem === e ? ' selected' : '') + '>' + e + '</option>';
    }
    html += '</select></div></div>';
    // 应用筛选
    let filtered = pets;
    if (this._filterKw) filtered = filtered.filter(p => p.name.includes(this._filterKw));
    if (this._filterElem === 'leader') { const lm = this._buildLeaderMap(); filtered = filtered.filter(p => lm[p.name]); }
    else if (this._filterElem) filtered = filtered.filter(p => (p.element||[]).includes(this._filterElem));
    html += '<div class="card-grid">';
    for (const p of filtered) {
      const elems = (p.element || []).map(e => '<span class="card-tag">' + this._esc(e) + '</span>').join('');
      const img = p.image ? '<img class="card-img" src="' + this._esc(p.image) + '" alt="" loading="lazy">' : '';
      const hasLeader = leaderMap[p.name] ? true : false;
      html += '<div class="card edit-card" onclick="Editor.openEdit(\'' + this._esc(p.name) + '\')">'
        + img
        + '<div class="card-name">' + this._esc(p.name) + '</div>'
        + '<div class="card-tags">' + elems + '</div>'
        + (p.stats ? '<div class="card-stats">种族 ' + (p.stats.total || '-') + '</div>' : '')
        + (p.skills ? '<div class="card-stats">' + p.skills.length + ' 个技能</div>' : '') + (hasLeader ? '<div class="card-stats" style="color:var(--primary-500)">\u{1F451} 有首领形态</div>' : '')
        + '<span class="edit-badge">编辑</span>'
        + '</div>';
    }
    html += '</div>';
    this._container.innerHTML = html;
  },

  /** 打开编辑面板 */
  openEdit(name) {
    const pet = this._data.pets.find(p => p.name === name);
    if (!pet) return;

    const st = pet.stats || {};
    const elemsAll = ['普通','草','火','水','光','机械','地','冰','龙','电','毒','虫','武','翼','萌','幽','恶','幻'];
    const ELEM_COLORS = {
      '火':'#FF6D00','水':'#1565C0','草':'#2E7D32','光':'#F9A825','普通':'#757575',
      '机械':'#37474F','地':'#795548','冰':'#00ACC1','龙':'#6A1B9A','电':'#FF8F00',
      '毒':'#AD1457','虫':'#558B2F','武':'#DD2C00','翼':'#0277BD','萌':'#E91E63',
      '幽':'#4527A0','恶':'#424242','幻':'#00695C'
    };

    let html = '<div class="edit-overlay" onclick="if(event.target===this)Editor.closeEdit()">'
      + '<div class="edit-panel">'
      + '<button class="edit-close" onclick="Editor.closeEdit()">&times;</button>'
      + '<h2>编辑：' + this._esc(pet.name) + '</h2>'
      + '<div class="edit-form">'

      // 名称
      + '<label>名称</label>'
      + '<input id="edit-name" value="' + this._esc(pet.name) + '">'

      // 属性
      + '<label>属性</label>'
      + '<div id="edit-elements">';
    for (const e of elemsAll) {
      const active = (pet.element || []).includes(e);
      html += '<span class="edit-elem-tag" style="display:inline-block;padding:2px 10px;margin:2px;border-radius:12px;font-size:12px;cursor:pointer;'
        + (active ? 'background:' + (ELEM_COLORS[e] || '#ccc') + ';color:#fff;' : 'background:var(--neutral-100);color:var(--neutral-500);')
        + '" onclick="Editor.toggleElem(\'' + this._esc(e) + '\')">' + e + '</span>';
    }
    html += '</div>'

      // 图片URL
      + '<label>图片URL</label>'
      + '<div style="display:flex;gap:8px;align-items:center">'
      + '<input id="edit-image" value="' + this._esc(pet.image || '') + '" style="flex:1" placeholder="图片URL">'
      + (pet.image ? '<img class="edit-image-preview" src="' + this._esc(pet.image) + '" onclick="document.getElementById(\'edit-image\').value=prompt(\'输入新图片URL:\',this.src);Editor.previewImage()">' : '')
      + '</div>'

      // 首领形态
      + '<label style="align-self:start">👑 首领</label>'
      + '<div id="edit-leader-section">' + this._renderLeaderSection(pet) + '</div>'

      // 描述
      + '<label>描述</label>'
      + '<textarea id="edit-desc">' + this._esc(pet.description || '') + '</textarea>'

      // 种族值
      + '<label>生命</label><input id="stat-hp" type="number" value="' + (st.hp ?? 0) + '">'
      + '<label>物攻</label><input id="stat-attack" type="number" value="' + (st.attack ?? 0) + '">'
      + '<label>魔攻</label><input id="stat-magic_attack" type="number" value="' + (st.magic_attack ?? 0) + '">'
      + '<label>物防</label><input id="stat-defense" type="number" value="' + (st.defense ?? 0) + '">'
      + '<label>魔防</label><input id="stat-magic_defense" type="number" value="' + (st.magic_defense ?? 0) + '">'
      + '<label>速度</label><input id="stat-speed" type="number" value="' + (st.speed ?? 0) + '">'

      // 技能列表
      + '<label style="align-self:start;margin-top:8px">技能</label>'
      + '<div id="edit-skills"><div class="skill-list">';

    // 编辑中的临时数据
    this._editingPet = pet.name;
    this._editElems = [...(pet.element || [])];
    this._editSkills = (pet.skills || []).map(s => ({...s}));

    for (const sk of this._editSkills) {
      html += '<div class="skill-edit-item">'
        + '<input value="' + this._esc(sk.name) + '" onchange="Editor.editSkillName(\'' + this._esc(sk.name) + '\',this.value)" placeholder="技能名">'
        + '<select onchange="Editor.editSkillField(\'' + this._esc(sk.name) + '\',\'element\',this.value)">'
        + '<option value="">系别</option>';
      for (const e of elemsAll) {
        html += '<option value="' + e + '"' + (sk.element === e ? ' selected' : '') + '>' + e + '</option>';
      }
      html += '</select>'
        + '<select onchange="Editor.editSkillField(\'' + this._esc(sk.name) + '\',\'category\',this.value)">'
        + '<option value="">分类</option>'
        + '<option value="物攻"' + (sk.category === '物攻' ? ' selected' : '') + '>物攻</option>'
        + '<option value="魔攻"' + (sk.category === '魔攻' ? ' selected' : '') + '>魔攻</option>'
        + '<option value="状态"' + (sk.category === '状态' ? ' selected' : '') + '>状态</option>'
        + '<option value="防御"' + (sk.category === '防御' ? ' selected' : '') + '>防御</option>'
        + '</select>'
        + '<input type="number" value="' + (sk.power ?? '') + '" onchange="Editor.editSkillField(\'' + this._esc(sk.name) + '\',\'power\',this.value)" placeholder="威力" style="width:50px">'
        + '<input type="number" value="' + (sk.cost ?? '') + '" onchange="Editor.editSkillField(\'' + this._esc(sk.name) + '\',\'cost\',this.value)" placeholder="PP" style="width:50px">'
        + '<button class="skill-edit-remove" onclick="Editor.removeSkill(\'' + this._esc(sk.name) + '\')">x</button>'
        + '</div>';
    }

    html += '</div>'
      + '<div class="skill-add-row">'
      + '<input id="new-skill-name" placeholder="新技能名">'
      + '<button class="btn-sm" onclick="Editor.addSkill()">添加</button>'
      + '</div>'
      + '</div>'

      // 保存按钮
      + '</div>'
      + '<div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">'
      + '<button class="btn" onclick="Editor.savePet(\'' + this._esc(pet.name) + '\')">保存修改</button>'
      + '<button class="btn-filter" onclick="Editor.closeEdit()">取消</button>'
      + '</div>'
      + '</div></div>';

    // Append overlay
    const div = document.createElement('div');
    div.innerHTML = html;
    document.body.appendChild(div.firstElementChild);
  },

  closeEdit() {
    const overlay = document.querySelector('.edit-overlay');
    if (overlay) overlay.remove();
    this._editingPet = null;
  },

  toggleElem(e) {
    const idx = this._editElems.indexOf(e);
    if (idx >= 0) this._editElems.splice(idx, 1);
    else this._editElems.push(e);
    // Refresh element display
    const tags = document.querySelectorAll('.edit-elem-tag');
    const ELEM_COLORS = {
      '火':'#FF6D00','水':'#1565C0','草':'#2E7D32','光':'#F9A825','普通':'#757575',
      '机械':'#37474F','地':'#795548','冰':'#00ACC1','龙':'#6A1B9A','电':'#FF8F00',
      '毒':'#AD1457','虫':'#558B2F','武':'#DD2C00','翼':'#0277BD','萌':'#E91E63',
      '幽':'#4527A0','恶':'#424242','幻':'#00695C'
    };
    tags.forEach(el => {
      const elem = el.textContent.trim();
      const active = this._editElems.includes(elem);
      el.style.background = active ? (ELEM_COLORS[elem] || '#ccc') : 'var(--neutral-100)';
      el.style.color = active ? '#fff' : 'var(--neutral-500)';
    });
  },

  savePet(name) {
    const pet = this._data.pets.find(p => p.name === name);
    if (!pet) return;

    pet.name = document.getElementById('edit-name').value.trim() || pet.name;
    pet.element = [...this._editElems];
    pet.image = document.getElementById('edit-image').value.trim() || null;
    pet.description = document.getElementById('edit-desc').value.trim() || '';

    const st = pet.stats || {};
    ['hp','attack','magic_attack','defense','magic_defense','speed'].forEach(f => {
      const val = parseInt(document.getElementById('stat-' + f)?.value);
      if (!isNaN(val)) st[f] = val;
    });
    st.total = (st.hp||0)+(st.attack||0)+(st.magic_attack||0)+(st.defense||0)+(st.magic_defense||0)+(st.speed||0);
    pet.stats = st;
    pet.skills = this._editSkills.filter(s => s.name.trim());
    pet.skills_count = pet.skills.length;
    this._dirty = true;
    this.closeEdit();
    this.render();

    // 增量保存 - 只发这个精灵的数据
    const btn = document.querySelector('.btn');
    const status = document.getElementById('saveStatus');
    status.textContent = '保存中...';
    fetch('/save-pet', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(pet)
    }).then(r => r.json()).then(() => {
      status.textContent = '✎ 已增量保存';
    }).catch(() => {
      status.textContent = '✎ 本地已修改（服务器保存失败）';
    });
  },

  editSkillName(oldName, newName) {
    const sk = this._editSkills.find(s => s.name === oldName);
    if (sk) sk.name = newName;
  },

  editSkillField(skillName, field, val) {
    const sk = this._editSkills.find(s => s.name === skillName);
    if (sk) {
      if (field === 'power' || field === 'cost') {
        sk[field] = val ? parseInt(val) : null;
      } else {
        sk[field] = val;
      }
    }
  },

  removeSkill(name) {
    this._editSkills = this._editSkills.filter(s => s.name !== name);
    // Re-render the skills list
    const container = document.querySelector('#edit-skills .skill-list');
    if (container) {
      // Rebuild from this._editSkills
      const elemsAll = ['普通','草','火','水','光','机械','地','冰','龙','电','毒','虫','武','翼','萌','幽','恶','幻'];
      let html = '';
      for (const sk of this._editSkills) {
        html += '<div class="skill-edit-item">'
          + '<input value="' + this._esc(sk.name) + '" onchange="Editor.editSkillName(\'' + this._esc(sk.name) + '\',this.value)" placeholder="技能名">'
          + '<select onchange="Editor.editSkillField(\'' + this._esc(sk.name) + '\',\'element\',this.value)">'
          + '<option value="">系别</option>';
        for (const e of elemsAll) {
          html += '<option value="' + e + '"' + (sk.element === e ? ' selected' : '') + '>' + e + '</option>';
        }
        html += '</select>'
          + '<select onchange="Editor.editSkillField(\'' + this._esc(sk.name) + '\',\'category\',this.value)">'
          + '<option value="">分类</option>'
          + '<option value="物攻"' + (sk.category === '物攻' ? ' selected' : '') + '>物攻</option>'
          + '<option value="魔攻"' + (sk.category === '魔攻' ? ' selected' : '') + '>魔攻</option>'
          + '<option value="状态"' + (sk.category === '状态' ? ' selected' : '') + '>状态</option>'
          + '<option value="防御"' + (sk.category === '防御' ? ' selected' : '') + '>防御</option>'
          + '</select>'
          + '<input type="number" value="' + (sk.power ?? '') + '" onchange="Editor.editSkillField(\'' + this._esc(sk.name) + '\',\'power\',this.value)" placeholder="威力" style="width:50px">'
          + '<input type="number" value="' + (sk.cost ?? '') + '" onchange="Editor.editSkillField(\'' + this._esc(sk.name) + '\',\'cost\',this.value)" placeholder="PP" style="width:50px">'
          + '<button class="skill-edit-remove" onclick="Editor.removeSkill(\'' + this._esc(sk.name) + '\')">x</button>'
          + '</div>';
      }
      container.innerHTML = html;
    }
  },

  addSkill() {
    const input = document.getElementById('new-skill-name');
    const name = input.value.trim();
    if (!name) return;
    this._editSkills.push({ name, element: '', category: '', cost: null, power: null, effect: '', source: '' });
    input.value = '';
    this.removeSkill('__dummy__'); // Trigger re-render
  },

  previewImage() {
    const input = document.getElementById('edit-image');
    const preview = document.querySelector('.edit-image-preview');
    if (preview && input.value) preview.src = input.value;
  },

  async saveAll() {
    const btn = document.querySelector('.btn');
    const status = document.getElementById('saveStatus');
    btn.disabled = true;
    status.textContent = '保存中...';
    status.className = '';

    try {
      const resp = await fetch('/save-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this._data)
      });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      status.textContent = '✅ 保存成功！主项目数据已同步';
      status.className = 'save-success';
      this._dirty = false;
    } catch (e) {
      status.textContent = '❌ 保存失败: ' + e.message;
      status.className = 'save-error';
    }
    btn.disabled = false;
  },


  _renderLeaderSection(pet) {
    const leaderMap = this._buildLeaderMap();
    const pets = this._data?.pets || [];
    const myLeader = leaderMap[pet.name];
    let baseName = '';
    const m = pet.name.match(/^(.+)（首领形态[^）]*）/);
    if (m) baseName = m[1];
    if (!myLeader && pet.name.startsWith('首领化')) baseName = pet.name.slice(3);

    let html = '<div style="display:flex;flex-direction:column;gap:6px">';
    if (myLeader) {
      html += '<div style="font-size:12px;display:flex;align-items:center;gap:8px">'
        + '<span style="background:var(--primary-50);padding:3px 10px;border-radius:6px;font-weight:600">首领形态: ' + this._esc(myLeader) + '</span>'
        + '<button class="btn-sm" onclick="Editor.openEdit(\'' + this._esc(myLeader) + '\')">编辑首领</button>'
        + '</div>';
    } else if (baseName) {
      html += '<div style="font-size:12px">此为 ' + this._esc(baseName) + ' 的首领形态</div>';
    } else {
      html += '<div style="font-size:12px;color:var(--neutral-500)">暂无首领形态</div>';
    }
    html += '<div style="display:flex;gap:6px;align-items:center;margin-top:4px">'
      + '<select id="edit-leader-target" style="flex:1;padding:4px 6px;border:1px solid var(--neutral-200);border-radius:6px;font-size:12px">'
      + '<option value="">设置关联...</option>';
    for (const c of pets) {
      if (c.name === pet.name) continue;
      html += '<option value="' + this._esc(c.name) + '">' + this._esc(c.name) + '</option>';
    }
    html += '</select>'
      + '<button class="btn-sm" onclick="Editor.associateLeader(\'' + this._esc(pet.name) + '\')">关联</button>'
      + '<button class="btn-filter" onclick="Editor.openEdit(\'' + this._esc(pet.name) + '\')">刷新</button>'
      + '</div></div>';
    return html;
  },

  associateLeader(baseName) {
    const sel = document.getElementById('edit-leader-target');
    if (!sel || !sel.value) return;
    const leaderName = sel.value;
    alert('首领形态关联需要在精灵名中体现。\n请将 "' + leaderName + '" 的名称修改为包含 "' + baseName + '（首领形态）" 的格式。');
    this.closeEdit();
    this.openEdit(leaderName);
  },

  /** 去除精灵名中的括号标注词 */
  _stripNameSuffix(name) {
    return name.replace(/[（(][^）)]*[）)]/g, '').trim();
  },

  _buildLeaderMap() {
    const map = {};
    const pets = this._data?.pets || [];
    for (const p of pets) {
      const n = p.name;
      const m = n.match(/^(.+)（首领形态[^）]*）/);
      if (m) { map[m[1]] = n; continue; }
      if (n.startsWith('首领化')) { map[n.slice(3)] = n; }
    }
    // 补充：带括号标注的精灵也映射到同名基础精灵的首领
    for (const p of pets) {
      const base = this._stripNameSuffix(p.name);
      if (base !== p.name && map[base]) {
        map[p.name] = map[base];
      }
    }
    return map;
  },


  /** 当前标签页 */
  _currentTab: 'pets',

  showTab(tab) {
    this._currentTab = tab;
    document.querySelectorAll('#editorNav [data-tab]').forEach(el => {
      el.style.fontWeight = el.dataset.tab === tab ? '700' : '';
      el.style.color = el.dataset.tab === tab ? 'var(--primary-500)' : 'var(--neutral-500)';
    });
    if (tab === 'skills') this.renderSkills();
    else if (tab === 'check') this.checkData();
    else this.render();
  },

  _toggleSortSkill() {
    this._sortSkillBy = this._sortSkillBy === 'count' ? null : 'count';
    this.renderSkills();
  },

  renderSkills() {
    const pets = this._data?.pets || [];
    // 收集所有唯一技能（按名称去重）
    const skillMap = {};
    for (const p of pets) {
      for (const s of (p.skills || [])) {
        if (!s.name) continue;
        if (!skillMap[s.name]) {
          skillMap[s.name] = { ...s, _pets: [] };
        }
        if (!skillMap[s.name]._pets.includes(p.name)) {
          skillMap[s.name]._pets.push(p.name);
        }
      }
    }
    const skills = Object.values(skillMap).sort((a, b) => this._sortSkillBy === 'count' ? (b._pets||[]).length - (a._pets||[]).length : a.name.localeCompare(b.name));
    const kw = (this._skillKw || '').toLowerCase();
    const filtered = kw ? skills.filter(s => s.name.includes(kw) || (s.element||'').includes(kw) || (s.category||'').includes(kw)) : skills;

    let html = '<div class="page-header"><h2>技能管理</h2><p>共 ' + skills.length + ' 个唯一技能 · 修改后同步到所有精灵</p></div>';
    html += '<input class="builder-search" placeholder="搜索技能名/系别..." value="' + this._esc(this._skillKw || '') + '" oninput="Editor._skillKw=this.value;Editor.renderSkills()" style="margin-bottom:12px;width:100%;max-width:400px">';
    html += '<div style="overflow-x:auto">';
    html += '<table class="skill-table" style="width:100%"><thead><tr>'
      + '<th>技能名</th><th>系别</th><th>分类</th><th>能耗</th><th>威力</th><th>效果</th><th style="cursor:pointer" onclick="Editor._toggleSortSkill()">使用 &#9650;&#9660;</th><th>操作</th>'
      + '</tr></thead><tbody>';
    for (const sk of filtered) {
      html += '<tr>'
        + '<td><strong>' + this._esc(sk.name) + '</strong></td>'
        + '<td>' + this._esc(sk.element || '-') + '</td>'
        + '<td>' + this._esc(sk.category || '-') + '</td>'
        + '<td>' + (sk.cost != null ? sk.cost : '-') + '</td>'
        + '<td>' + (sk.power != null ? sk.power : '-') + '</td>'
        + '<td class="skill-effect">' + this._esc((sk.effect || '').slice(0, 40)) + '</td>'
        + '<td style="font-size:11px;color:var(--neutral-500);max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + this._esc((sk._pets||[]).join(', ')) + '">' + (sk._pets||[]).length + ' 只</td>'
        + '<td><button class="btn-sm" onclick="Editor.openSkillEdit(\'' + this._esc(sk.name) + '\')">编辑</button></td>'
        + '</tr>';
    }
    html += '</tbody></table></div>';
    if (!filtered.length) html += '<div class="empty-state">未找到匹配的技能</div>';
    this._container.innerHTML = html;
  },

  openSkillEdit(name) {
    const pets = this._data?.pets || [];
    // 找到这个技能的完整数据
    let skillData = null;
    for (const p of pets) {
      const s = (p.skills||[]).find(x => x.name === name);
      if (s) { skillData = { ...s }; break; }
    }
    if (!skillData) return;

    const affected = [];
    for (const p of pets) {
      if ((p.skills||[]).some(s => s.name === name)) affected.push(p.name);
    }

    let html = '<div class="edit-overlay" onclick="if(event.target===this)Editor.closeSkillEdit()">'
      + '<div class="edit-panel" style="max-width:600px">'
      + '<button class="edit-close" onclick="Editor.closeSkillEdit()">&times;</button>'
      + '<h2>编辑技能：' + this._esc(name) + '</h2>'
      + '<div style="font-size:12px;color:var(--neutral-500);margin-bottom:12px">将同步修改到 <strong>' + affected.length + '</strong> 只精灵：' + this._esc(affected.join(', ')) + '</div>'
      + '<div class="edit-form">'
      + '<label>技能名</label><input id="sk-name" value="' + this._esc(skillData.name) + '">'
      + '<label>系别</label><select id="sk-element">';
    const ELEMS = ['','普通','草','火','水','光','机械','地','冰','龙','电','毒','虫','武','翼','萌','幽','恶','幻'];
    for (const e of ELEMS) {
      html += '<option value="' + e + '"' + (skillData.element === e ? ' selected' : '') + '>' + (e || '-') + '</option>';
    }
    html += '</select>'
      + '<label>分类</label><select id="sk-category">';
    for (const cat of ['','物攻','魔攻','状态','防御']) {
      html += '<option value="' + cat + '"' + (skillData.category === cat ? ' selected' : '') + '>' + (cat || '-') + '</option>';
    }
    html += '</select>'
      + '<label>能耗</label><input id="sk-cost" type="number" value="' + (skillData.cost ?? '') + '">'
      + '<label>威力</label><input id="sk-power" type="number" value="' + (skillData.power ?? '') + '">'
      + '<label>效果</label><textarea id="sk-effect" rows="3">' + this._esc(skillData.effect || '') + '</textarea>'
      + '<label>解锁</label><input id="sk-source" value="' + this._esc(skillData.source || '') + '">'
      + '</div>'
      + '<div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">'
      + '<button class="btn" onclick="Editor.saveSkill(\'' + this._esc(name) + '\')">保存修改</button>'
      + '<button class="btn-filter" onclick="Editor.closeSkillEdit()">取消</button>'
      + '</div></div></div>';

    const div = document.createElement('div');
    div.innerHTML = html;
    document.body.appendChild(div.firstElementChild);
    this._editingSkill = name;
  },

  closeSkillEdit() {
    const overlay = document.querySelector('.edit-overlay');
    if (overlay) overlay.remove();
    this._editingSkill = null;
  },

  saveSkill(name) {
    // 读取表单数据
    const newName = document.getElementById('sk-name').value.trim() || name;
    const element = document.getElementById('sk-element').value;
    const category = document.getElementById('sk-category').value;
    const cost = document.getElementById('sk-cost').value;
    const power = document.getElementById('sk-power').value;
    const effect = document.getElementById('sk-effect').value.trim() || '';
    const source = document.getElementById('sk-source').value.trim() || '';

    // 更新所有精灵的这个技能
    const pets = this._data?.pets || [];
    
    // 冲突检测
    if (newName !== name) {
      const pets = this._data?.pets || [];
      let conflict = false;
      for (const p of pets) {
        if ((p.skills||[]).some(s => s.name === newName)) { conflict = true; break; }
      }
      if (conflict && !confirm('冲突：技能 ' + newName + ' 已存在，继续将合并同名技能。是否继续？')) return;
    }

let count = 0;
    for (const p of pets) {
      for (const s of (p.skills || [])) {
        if (s.name === name) {
          s.name = newName;
          s.element = element;
          s.category = category;
          s.cost = cost !== '' ? parseInt(cost) : null;
          s.power = power !== '' ? parseInt(power) : null;
          s.effect = effect;
          s.source = source;
          count++;
          break;
        }
      }
    }

    this._dirty = true;
    this.closeSkillEdit();
    this.renderSkills();
    document.getElementById('saveStatus').textContent = '\u270E 已修改 ' + count + ' 个技能实例';
    document.getElementById('saveStatus').className = '';
  },

  _esc(str) {
    return String(str).replace(/[&<>"']/g, c =>
      ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' })[c]
    );
  }
};

// 启动
document.addEventListener('DOMContentLoaded', () => Editor.init());
