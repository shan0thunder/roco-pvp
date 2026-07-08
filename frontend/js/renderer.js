/**
 * 洛克王国世界PVP助手 — 视图渲染器
 * ======================================
 * 所有页面视图 + 配队构建器
 */

const Renderer = {
  _container: null,
  _searchInput: null,
  _searchBar: null,
  _navItems: null,

  // 配队状态
  _team: [],
  _teamSkills: {},
  _teamWill: {},
  _teamLeader: {},
  _leaderMap: null,
  _slotOptionMode: null,
  _petNature: {},
  _teamStats: {},  // 每只精灵选中的种族值 { slotIndex: ['speed','attack'] } 最多3个
  _selectedSlot: null,
  _expandedPet: null,
  _petFilterElem: '',
  _petFilterFunc: '',
  _petFilterLeader: false,
  _petSortBy: null,
  _skillIndex: null,  // 技能索引缓存

  // 阵容分享
  _shareSortBy: 'new',  // 排序: new|click|cover|resist
  _shareShowMine: false, // true=只显示我的阵容
  _shareShowFav: false, // true=只显示收藏
  _shareDialog: null,   // 分享弹窗DOM

  // 配队器筛选
  _builderFilter: null,
  _builderCollapsed: window.innerWidth < 768,  // 手机端默认折叠
  _dragSkillData: null,
  _dragSlotIdx: null,
  _searchKw: '',
  _searchTimer: null,
  _dragTarget: null, _dragOffX: 0, _dragOffY: 0,
  _searchComposing: false,  // IME输入法组合中

  init() {
    this._container = document.getElementById('mainContent');
    this._searchInput = document.getElementById('searchInput');
    this._searchBar = document.getElementById('searchBar');
    this._navItems = document.querySelectorAll('.nav-item');

    this._navItems.forEach(el => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        const route = el.dataset.route;
        if (route) {
          Router.go(route);
          this._renderCurrentView();
        }
      });
    });

    // 搜索输入：IME兼容（composition期间不触发重渲染）
    this._searchInput?.addEventListener('compositionstart', () => { this._searchComposing = true; });
    this._searchInput?.addEventListener('compositionend', () => {
      this._searchComposing = false;
      this._onSearchInput();
    });
    this._searchInput?.addEventListener('input', () => {
      this._searchKw = this._searchInput.value;
      if (!this._searchComposing) {
        this._onSearchInput();
      }
    });

    document.addEventListener('click', () => {
      document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
    });
  },

  /** 配队器拖拽 */
  _enableDrag(el) {
    if (!el) return;
    el.classList.add('drag-enabled');
    el.addEventListener('mousedown', (e) => this._dragStart(e));
    el.addEventListener('touchstart', (e) => this._dragStart(e), {passive: true});
  },

  _dragStart(e) {
    const target = e.currentTarget;
    if (e.target.closest('.btn,.btn-sm,.btn-filter,.bar-slot,.card,.filter-select')) return;
    const touch = e.touches?.[0];
    this._dragTarget = target;
    this._dragOffX = (touch?.clientX || e.clientX) - target.getBoundingClientRect().left;
    this._dragOffY = (touch?.clientY || e.clientY) - target.getBoundingClientRect().top;
    target.style.cursor = 'grabbing';
    target.style.userSelect = 'none';
    document.addEventListener('mousemove', this._dragMove = this._dragMove.bind(this));
    document.addEventListener('mouseup', this._dragEnd = this._dragEnd.bind(this));
    document.addEventListener('touchmove', this._dragMove, {passive: true});
    document.addEventListener('touchend', this._dragEnd);
    // 提示已放到展开时触发
  },

  _dragMove(e) {
    if (!this._dragTarget) return;
    const touch = e.touches?.[0];
    const x = (touch?.clientX || e.clientX) - this._dragOffX;
    const y = (touch?.clientY || e.clientY) - this._dragOffY;
    this._dragTarget.style.position = 'fixed';
    this._dragTarget.style.left = Math.max(0, x) + 'px';
    this._dragTarget.style.top = Math.max(0, y) + 'px';
    this._dragTarget.style.zIndex = '100';
    this._dragTarget.style.width = this._dragTarget.offsetWidth + 'px';
  },

  _dragEnd() {
    if (!this._dragTarget) return;
    this._dragTarget.style.cursor = '';
    this._dragTarget.style.userSelect = '';
    this._dragTarget = null;
    document.removeEventListener('mousemove', this._dragMove);
    document.removeEventListener('mouseup', this._dragEnd);
    document.removeEventListener('touchmove', this._dragMove);
    document.removeEventListener('touchend', this._dragEnd);
  },

  _setActiveNav(route) {
    this._navItems.forEach(el => {
      el.classList.toggle('active', el.dataset.route === route);
    });
  },

  _showSearch(show) {
    this._searchBar.style.display = show ? 'flex' : 'none';
    if (show) this._searchInput.value = '';
  },

  _keyword() { return (this._searchKw || '').toLowerCase(); },

  async _renderCurrentView() {
    const { route, params } = Router.parse();
    this._setActiveNav(route);
    if (route !== 'pets' && route !== 'builder') this._expandedPet = null;

    try {
      switch (route) {
        case 'pets':
          this._showSearch(false);
          await this._renderPetList();
          break;
        case 'pet':
          this._showSearch(false);
          await this._renderPetDetail(params[0]);
          break;
        case 'skills':
          this._showSearch(false);
          await this._renderSkills();
          break;
        case 'share':
          this._showSearch(false);
          await this._renderSharePage();
          break;
        case 'other':
          this._showSearch(false);
          this._renderOtherPage();
          break;
        case 'type-chart':
          this._showSearch(false);
          await this._renderTypeChart();
          break;
        default:
          this._container.innerHTML = '<div class="empty-state">页面不存在</div>';
      }
    } catch (e) {
      console.error('渲染失败', e);
      this._container.innerHTML = '<div class="empty-state">数据加载失败，请确认已运行 python cli.py export-product</div>';
    }
  },

  // ==========================================================
  // 精灵图鉴列表 (含配队器面板)
  // ==========================================================
  async _renderPetList() {
    const data = await DataStore.load();
    // 尝试恢复队伍快照（仅首次加载）
    if (this._team.length === 0) {
      this._loadTeamSnapshot();
    }
    let pets = DataStore.pets;

    const kw = this._searchKw || '';
    if (kw) {
      pets = pets.filter(p => p.name.includes(kw) || (p.element||[]).some(e => e.includes(kw)));
    }

    if (this._petFilterElem) {
      pets = pets.filter(p => (p.element||[]).includes(this._petFilterElem));
    }

    // 功能标签
    const funcPets = {印记:new Set(),清印记:new Set(),清强化:new Set()};
    for (const p of DataStore.pets) {
      for (const s of (p.skills||[])) {
        const e = (s.effect||'')+(s.name||'');
        if (e.includes('印记')||e.includes('标记')) funcPets.印记.add(p.name);
        if ((e.includes('清除')||e.includes('驱散'))&&(e.includes('印记')||e.includes('标记'))) funcPets.清印记.add(p.name);
        if (e.includes('驱散')||e.includes('清除强化')||e.includes('清强化')) funcPets.清强化.add(p.name);
      }
    }
    if (!this._petFilterElem) this._petFilterElem = '';
    if (this._petFilterFunc) {
      const names = funcPets[this._petFilterFunc] || new Set();
      pets = pets.filter(p => names.has(p.name));
    }
    if (this._petFilterLeader) {
      this._buildLeaderMap();
      const lm = this._leaderMap || {};
      const leaderSet = new Set(Object.values(lm));
      pets = pets.filter(p => lm[p.name] || leaderSet.has(p.name));
    }

    const countEl = document.getElementById('searchCount');
    countEl.textContent = kw ? `找到 ${pets.length} 只精灵` : `共 ${DataStore.pets.length} 只精灵`;

    const chart = DataStore.typeChart || {};
    const allElems = DataStore.elements || [];
    const teamElems = [];
    for (const p of this._team) {
      for (const e of (p.element || [])) {
        if (!teamElems.includes(e)) teamElems.push(e);
      }
    }
    const cover = {};
    for (const atk of teamElems) {
      for (const def of allElems) {
        if ((chart[atk]||{})[def] >= 2) cover[def] = true;
      }
    }
    const coverGap = allElems.filter(e => !cover[e]);
    const highThreat = [];
    for (const atk of allElems) {
      let count = 0;
      for (const p of this._team) {
        const eff = this._calcEffectiveness(atk, p);
        if (eff > 1.0) count++;
      }
      if (count >= 2) highThreat.push(atk);
    }
    const noResist = [];
    for (const atk of allElems) {
      let hasResist = false;
      for (const p of this._team) {
        const eff = this._calcEffectiveness(atk, p);
        if (eff <= 0.5) { hasResist = true; break; }
      }
      if (!hasResist) noResist.push(atk);
    }

    const isCollapsed = this._builderCollapsed;

    let html = '<div class="builder-bar'+(isCollapsed?' collapsed':'')+'">'
      + '<div class="builder-bar-row title-row">'
      + '<span class="builder-bar-title">队伍 ('+this._team.length+'/6)</span>'
      + (this._team.length && isCollapsed ? '' : (this._team.length ? '<button class="btn-sm" onclick="Renderer._clearTeam();Renderer._renderCurrentView()">清空</button>' : ''))
      + (!isCollapsed ? '<button class="btn-sm" onclick="Renderer._favTeamFromBuilder()">⭐ 收藏</button>' : '')
      + (!isCollapsed ? '<button class="btn-sm" style="margin-left:auto" onclick="Renderer._openShareDialog()">分享</button>' : '')
      + (!isCollapsed ? '<button class="btn-sm" onclick="Renderer._exportTeam()">导出</button>' : '');

    // 折叠/展开按钮
    html += '<button class="btn-sm" onclick="Renderer._builderCollapsed=!Renderer._builderCollapsed;Renderer._renderCurrentView()">'+(isCollapsed?'+ 展开':'− 折叠')+'</button>';

    html += '</div>';

    if (isCollapsed) {
      // 折叠模式
      if (this._team.length > 0) {
        html += '<div class="builder-bar-row collapsed-slots" style="display:flex;flex-wrap:wrap;gap:4px;padding:4px 0">';
        for (let i = 0; i < this._team.length; i++) {
          const p = this._team[i];
          if (!p) continue;
          const elTags = (p.element||[]).map(e => '<span class="card-tag" style="background:'+Utils.elementColor(e)+';color:#fff;font-size:9px;padding:0 4px">'+Utils.esc(e)+'</span>').join('');
          html += '<span style="cursor:pointer;font-size:13px;padding:2px 6px;border-radius:4px;background:var(--neutral-50);border:1px solid var(--neutral-200)" onclick="Renderer._showSlotDetail('+i+')">'
            + Utils.esc(p.name)+' '+elTags+'</span>';
        }
        html += '</div>';
      }
    } else {
      // 展开模式：完整配队器
      html += '<div class="builder-bar-row toggle-row">'
        + '<button class="btn-filter'+(this._slotOptionMode==='will'?' active':'')+'" onclick="Renderer._slotOptionMode=Renderer._slotOptionMode===\'will\'?null:\'will\';Renderer._renderCurrentView()">愿力</button>'
        + '<button class="btn-filter'+(this._slotOptionMode==='leader'?' active':'')+'" onclick="Renderer._slotOptionMode=Renderer._slotOptionMode===\'leader\'?null:\'leader\';Renderer._renderCurrentView()">首领化</button>'
        + '</div>'
        + '<div class="builder-bar-row slots-row">';
      for (let i = 0; i < 6; i++) {
        const p = this._team[i];
        if (p) {
          const elTags = (p.element||[]).map(e => '<span class="card-tag" style="background:'+Utils.elementColor(e)+';color:#fff">'+Utils.esc(e)+'</span>').join('');
          html += '<div class="bar-slot filled" draggable="true" onclick="Renderer._showSlotDetail('+i+')" ondragstart="Renderer._dragSlotStart(event,'+i+')" ondragover="event.preventDefault()" ondrop="Renderer._dragSlotDrop(event,'+i+')">'
            + (p.image ? '<img class="bar-slot-img" src="'+Utils.esc(p.image)+'" alt="">' : '')
            + '<div class="bar-slot-name">'+Utils.esc(p.name)+'</div>'
            + '<div class="bar-slot-elems">'+elTags+'</div>'
            + '<button class="bar-slot-remove" onclick="event.stopPropagation();Renderer._removeFromTeam('+i+');Renderer._renderCurrentView()">−</button>'
            + '</div>';
        } else {
          html += '<div class="bar-slot empty" onclick="Renderer._openPetSelector()"><span class="bar-slot-placeholder">+</span></div>';
        }
      }
      html += '</div>'
        + '<div class="builder-bar-row config-row">'

    for (let i = 0; i < 6; i++) {
      const p = this._team[i];
      html += '<div class="bar-config-cell">';
      if (p && this._slotOptionMode === 'will') {
        const willVal = this._teamWill[i] || '';
        html += '<select class="bar-config-select" onchange="Renderer._teamWill['+i+']=this.value;Renderer._renderCurrentView()">'
          + '<option value="">愿力</option>';
        for (const we of allElems) {
          html += '<option value="'+we+'"'+(willVal===we?' selected':'')+'>'+we+'</option>';
        }
        html += '</select>';
      } else if (p && this._slotOptionMode === 'leader') {
        const leaderName = this._getLeaderName(p.name);
        if (leaderName) {
          html += '<span class="bar-config-leader" onclick="Renderer._toggleLeader('+i+');Renderer._renderCurrentView()">首领</span>';
        } else {
          html += '<span class="bar-config-empty"></span>';
        }
      } else {
        html += '<span class="bar-config-empty"></span>';
      }
      html += '</div>';
    }
    }  // 关闭展开模式 else 块
    if (!isCollapsed) {
    html += '</div>'
      + '<div class="builder-bar-row analysis-row">';
    const analysisBlocks = [
      { label: '打击面', tip: '队伍精灵的攻击属性所能克制的属性集合（×2）', items: Object.keys(cover), cls: 'tag-strong', tipMode: 'cover' },
      { label: '打击面缺口', tip: '队伍中所有属性均无法克制的属性，建议补对应攻击手', items: coverGap, cls: 'tag-weak', tipMode: 'gap' },
      { label: '高威胁属性', tip: '能克制队伍中2只及以上精灵的属性（最终倍率>1.0），建议补抵抗手', items: highThreat, cls: 'tag-danger', tipMode: 'threat' },
      { label: '无抵抗属性', tip: '没有任何精灵能抵抗的属性（最终倍率≤0.5），容易被对方克制系打穿', items: noResist, cls: 'tag-weak', tipMode: 'noResist' },
    ];
    for (const block of analysisBlocks) {
      html += '<div class="bar-analysis-block">'
        + '<span class="bar-analysis-label">' + block.label
        + '<span class="info-icon" title="'+Utils.esc(block.tip)+'">i</span>'
        + '</span>'
        + '<div class="bar-analysis-tags">';
      const showItems = block.items.slice(0, 8);
      const remaining = block.items.length - showItems.length;
      for (const e of showItems) {
        html += '<span class="analysis-dot ' + block.cls + '" style="background:' + Utils.elementColor(e) + '" title="'+Utils.esc(this._typeTooltip(e, block.tipMode))+'">'+Utils.esc(e)+'</span>';
      }
      if (remaining > 0) html += '<span class="analysis-dot-more">+'+remaining+'</span>';
      if (!block.items.length) html += '<span class="analysis-dot-none">无</span>';
      html += '</div></div>';
    }
    // 综合评分
    if (this._team.length >= 2) {
      const coverPct = allElems.length ? Math.round(Object.keys(cover).length / allElems.length * 100) : 0;
      const threatScore = Math.max(0, 100 - highThreat.length * 15 - noResist.length * 10);
      const overallScore = Math.min(100, Math.round((coverPct * 0.5 + threatScore * 0.5)));
      html += '<div class="bar-analysis-block" style="background:var(--primary-50);border-radius:var(--radius);padding:4px 8px">'
        + '<span class="bar-analysis-label">综合评分</span>'
        + '<div style="font-size:18px;font-weight:700;color:'+(overallScore>=70?'var(--success-500)':overallScore>=40?'var(--warning-500)':'var(--danger-500)')+'">'+overallScore+'</div>'
        + '<div style="font-size:9px;color:var(--neutral-500)">'+coverPct+'%打击面</div>'
        + '</div>';
    }
    }
    if (!isCollapsed) {
      html += '</div></div>';  // 关闭analysis-row和builder-bar
    } else {
      html += '</div>';  // 折叠模式只需关闭builder-bar
    }

    // Slot detail panel
    if (this._selectedSlot != null && this._team[this._selectedSlot]) {
      const sp = this._team[this._selectedSlot];
      const st = sp.stats || {};
      const elBadges = (sp.element||[]).map(e => '<span class="card-tag" style="background:'+Utils.elementColor(e)+';color:#fff">'+Utils.esc(e)+'</span>').join('');
      const skills = sp.skills || [];
      const petIdx = this._selectedSlot;
      const selectedSkills = this._teamSkills[petIdx] || [null, null, null, null];
      const NATURES = ['勇敢','开朗','固执','保守','胆小','沉着','大胆','温和','慎重','淘气','冷静','悠闲','狂妄','寂寞','天真'];
      const currentNature = this._petNature[petIdx] || '';

      html += '<div class="slot-detail-panel">'
        + '<div class="sd-col sd-col-pet">'
        + (sp.image ? '<div class="sd-pet-img-wrap"><img class="sd-pet-img" src="'+Utils.esc(sp.image)+'" alt=""></div>' : '')
        + '<div class="sd-pet-name">'+Utils.esc(sp.name)+'</div>'
        + '<div class="sd-pet-elems">'+elBadges+'</div>'
        + '<div class="sd-pet-stats"><div class="sd-stat-row">'
        + this._statItem(petIdx, st, 'hp', '生')
        + this._statItem(petIdx, st, 'attack', '攻')
        + this._statItem(petIdx, st, 'defense', '防')
        + this._statItem(petIdx, st, 'magic_attack', '魔攻')
        + this._statItem(petIdx, st, 'magic_defense', '魔防')
        + this._statItem(petIdx, st, 'speed', '速')
        + '</div></div></div>'
        + '<div class="sd-col sd-col-nature">'
        + '<div class="sd-col-title">性格</div>'
        + '<select class="sd-nature-select" onchange="Renderer._petNature['+petIdx+']=this.value;Renderer._renderCurrentView()">'
        + '<option value="">选择</option>';
      const STAT_NAMES = {hp:'生命',attack:'物攻',defense:'物防',magic_attack:'魔攻',magic_defense:'魔防',speed:'速度'};
      for (const [key, label] of Object.entries(STAT_NAMES)) {
        html += '<option value="'+key+'"'+(currentNature===key?' selected':'')+'>'+label+' ('+(st[key]??'-')+')</option>';
      }
      html += '</select>'
        + (sp.trait ? '<div class="sd-col-desc" style="font-size:11px;color:var(--neutral-500);line-height:1.5;padding:6px 4px;border-top:1px solid var(--neutral-100);margin-top:6px"><strong>'+Utils.esc(sp.trait.name)+'</strong><br>'+Utils.esc(sp.trait.desc)+'</div>' : '')
        + '</div>'
        + '<div class="sd-col sd-col-skills">'
        + '<div class="sd-col-title">技能</div>'
        + '<div class="skill-slot-grid"><div class="skill-slot-row">';
      for (let si = 0; si < 4; si++) {
        const sk = selectedSkills[si];
        if (sk) {
          html += '<div class="skill-slot filled" draggable="true" onclick="Renderer._removeTeamSkill('+petIdx+','+si+')" title="点击移除" ondragstart="Renderer._dragSkillStart(event,'+petIdx+','+si+')" ondragover="event.preventDefault()" ondrop="Renderer._dragSkillDrop(event,'+petIdx+','+si+')">'
            + '<span class="skill-slot-num">'+(si+1)+'</span>'
            + '<div class="skill-slot-name">'+Utils.esc(sk.name)+'</div>'
            + '<div class="skill-slot-meta">'+Utils.esc(sk.element||'-')+' '+Utils.esc(sk.category||'-')
            + (sk.power != null ? ' 威力'+sk.power : '')
            + (sk.cost != null ? ' 能耗'+sk.cost : '')+'</div>'
            + '<div class="skill-slot-effect">'+Utils.truncate(sk.effect||'',24)+'</div></div>';
        } else {
          html += '<div class="skill-slot empty" onclick="Renderer._assignTeamSkillAuto('+petIdx+')">'
            + '<span class="skill-slot-num">'+(si+1)+'</span>'
            + '<div class="skill-slot-placeholder">+</div></div>';
        }
        if (si === 1) html += '</div><div class="skill-slot-row">';
      }
      html += '</div></div></div>'
        + '<div class="sd-col sd-col-pool">'
        + '<div class="sd-col-title">技能池</div>'
        + '<div class="sd-pool-scroll">'
        + '<table class="skill-table"><thead><tr><th>名称</th><th>系别</th><th>分类</th><th>能耗</th><th>威力</th><th>效果</th></tr></thead><tbody>';
      for (const sk of skills) {
        const isUsed = selectedSkills.some(s => s && s.name === sk.name);
        html += '<tr class="'+(isUsed?'skill-row-used':'skill-row')+'" onclick="'+(isUsed?'':'Renderer._assignTeamSkill('+petIdx+',\''+Utils.esc(sk.name)+'\')')+'">'
          + '<td><strong>'+Utils.esc(sk.name)+'</strong></td>'
          + '<td>'+Utils.esc(sk.element||'-')+'</td>'
          + '<td>'+Utils.esc(sk.category||'-')+'</td>'
          + '<td>'+(sk.cost!=null?sk.cost:'-')+'</td>'
          + '<td>'+(sk.power!=null?sk.power:'-')+'</td>'
          + '<td class="skill-effect">'+Utils.truncate(sk.effect||'',50)+'</td></tr>';
      }
      html += '</tbody></table></div></div>'
        + '<button class="sd-close" onclick="Renderer._hideSlotDetail()">x</button>'
        + '</div>';
    }

    // 显示顶栏搜索框（避免内联搜索重渲染丢焦点）
    this._showSearch(true);
    if (this._searchInput) this._searchInput.value = this._searchKw || '';

    const allElements = [...new Set(DataStore.pets.flatMap(p => p.element || []))].sort();
    if (!this._petFilterElem) this._petFilterElem = '';
    if (!this._petFilterFunc) this._petFilterFunc = '';
    if (!this._petFilterLeader) this._petFilterLeader = false;

    html += '<div class="builder-filter-bar">'
      + '<div class="filter-row">'
      + '<button class="btn-filter'+(this._petFilterElem===''?' active':'')+'" onclick="Renderer._petFilterElem=\'\';Renderer._renderCurrentView()">全部</button>'
      + '<select class="filter-select" onchange="Renderer._petFilterElem=this.value;Renderer._renderCurrentView()">'
      + '<option value="">系别</option>';
    for (const e of allElements) {
      html += '<option value="'+e+'"'+(this._petFilterElem===e?' selected':'')+'>'+e+'</option>';
    }
    html += '</select>'
      + '<select class="filter-select" onchange="Renderer._petFilterFunc=this.value;Renderer._renderCurrentView()">'
      + '<option value="">功能向</option>'
      + '<option value="清印记"'+ (this._petFilterFunc==='清印记'?' selected':'') +'>清印记</option>'
      + '<option value="印记"'+(this._petFilterFunc==='印记'?' selected':'')+'>印记手</option>'
      + '<option value="清强化"'+(this._petFilterFunc==='清强化'?' selected':'')+'>清强化</option>'
      + '</select>'
      + '<button class="btn-filter'+(this._petFilterLeader?' active':'')+'" onclick="Renderer._petFilterLeader=!Renderer._petFilterLeader;Renderer._renderCurrentView()">首领</button>'
      + '<button class="btn-filter" onclick="Renderer._toggleSortSpeed()">'+(this._petSortBy==='speed'?'✓ 排速':'⏳ 排速')+'</button>'
      + '</div></div>';

    // Sort
    if (this._petSortBy === 'speed') {
      pets = [...pets].sort((a, b) => (b.stats?.speed||0) - (a.stats?.speed||0));
    }

    html += '<div class="page-header"><h2>精灵图鉴</h2><p>点击精灵查看详细信息与技能，点 + 加入队伍，支持右键更多操作</p></div>';
    html += '<div class="card-grid" id="petGrid">';

    for (const p of pets) {
      const elements = (p.element || []).map(e => `<span class="card-tag" style="background:${Utils.elementColor(e)};color:#fff">${Utils.esc(e)}</span>`).join('');
      const isExpanded = this._expandedPet && this._expandedPet.name === p.name && this._expandedPet.idx === DataStore.pets.indexOf(p);
      const img = p.image ? `<img class="card-img" src="${Utils.esc(p.image)}" alt="${Utils.esc(p.name)}" loading="lazy">` : '';

      if (isExpanded) {
        const st = p.stats || {};
        const skillsList = (p.skills || []).map(s =>
          `<tr><td><strong>${Utils.esc(s.name)}</strong></td>
            <td>${Utils.esc(s.element||'-')}</td>
            <td>${Utils.esc(s.category||'-')}</td>
            <td>${s.cost!=null?s.cost:'-'}</td>
            <td>${s.power!=null?s.power:'-'}</td>
            <td class="skill-effect">${Utils.truncate(s.effect||'',50)}</td></tr>`
        ).join('');
        html += `<div class="card card-expanded">
          <button class="card-expand-close" onclick="Renderer._collapsePetCard()">−</button>
          <div class="card-expand-inner">
            <div class="card-expand-top">
              <div class="card-expand-left">
                ${img}
                <div class="card-name">${Utils.esc(p.name)}</div>
                <div class="card-tags">${elements}</div>
                <button class="btn-sm" style="margin-top:6px" onclick="Renderer._addToTeam('${Utils.esc(p.name)}');Renderer._collapsePetCard()">加入队伍</button>
              </div>
              <div class="card-expand-right">
                <div class="pet-detail-stats"><div class="stat-row">
                  <div class="stat-item"><div class="label">生命</div><div class="value">${st.hp??'-'}</div></div>
                  <div class="stat-item"><div class="label">物攻</div><div class="value">${st.attack??'-'}</div></div>
                  <div class="stat-item"><div class="label">魔攻</div><div class="value">${st.magic_attack??'-'}</div></div>
                  <div class="stat-item"><div class="label">物防</div><div class="value">${st.defense??'-'}</div></div>
                  <div class="stat-item"><div class="label">魔防</div><div class="value">${st.magic_defense??'-'}</div></div>
                  <div class="stat-item"><div class="label">速度</div><div class="value">${st.speed??'-'}</div></div>
                </div></div>
                ${p.trait ? '<div class="card-expand-desc"><strong style="font-size:13px">特性：'+Utils.esc(p.trait.name)+'</strong><br>'+Utils.esc(p.trait.desc)+'</div>' : ''}
              </div>
            </div>
            <div class="card-expand-skills"><h5>技能池 (${(p.skills||[]).length})</h5>
              <div class="skills-scroll">
                <table class="skill-table"><thead><tr><th>名称</th><th>系别</th><th>分类</th><th>能耗</th><th>威力</th><th>效果</th></tr></thead><tbody>${skillsList}</tbody></table>
              </div>
            </div>
          </div>
        </div>`;
      } else {
        const stats = p.stats ? `种族: ${p.stats.total || '-'}` : '';
        const inTeam = this._team.some(t => t.name === p.name);
        html += `<div class="card" onclick="Renderer._expandPetCard('${Utils.esc(p.name)}')" oncontextmenu="event.preventDefault();Renderer._showCardMenu(event,'${Utils.esc(p.name)}')">
          ${inTeam ? '' : `<button class="card-add-btn" onclick="event.stopPropagation();Renderer._addToTeam('${Utils.esc(p.name)}')">&plus;</button>`}
          ${img}
          <div class="card-name">${Utils.esc(p.name)}</div>
          <div class="card-tags">${elements}</div>
          ${stats ? `<div class="card-stats">${stats}</div>` : ''}
          ${p.skills_count ? `<div class="card-stats">${p.skills_count} 个技能</div>` : ''}
        </div>`;
      }
    }
    html += '</div>';
    if (pets.length === 0) html += '<div class="empty-state">未找到匹配的精灵，试试其他关键词</div>';

    this._container.innerHTML = html;

    // 配队器可拖拽（仅手机端）
    if (window.innerWidth < 768) {
      const builder = this._container.querySelector('.builder-bar');
      const detail = this._container.querySelector('.slot-detail-panel');
      if (builder) this._enableDrag(builder);
      if (detail) this._enableDrag(detail);
      // 展开时显示拖拽提示
      if (builder && !this._builderCollapsed && !builder.dataset.expandHinted) {
        builder.dataset.expandHinted = '1';
        const hint = document.createElement('div');
        hint.textContent = '↕ 可拖动';
        hint.style.cssText = 'position:absolute;top:-18px;right:8px;font-size:10px;color:var(--primary-500);background:var(--primary-50);padding:2px 8px;border-radius:4px;opacity:0;transition:opacity 0.3s;z-index:20';
        builder.style.position = 'relative';
        builder.appendChild(hint);
        requestAnimationFrame(() => { hint.style.opacity = '1'; setTimeout(() => { hint.style.opacity = '0'; setTimeout(() => hint.remove(), 400); }, 1500); });
      }
    }

    // 属性表高亮 (if present)
    const t = document.getElementById('typeChartTable');
    if (t) {
      t.querySelectorAll('td').forEach(cell => {
        cell.addEventListener('mouseenter', function() {
          const row = this.parentElement;
          const idx = Array.from(row.children).indexOf(this);
          row.querySelectorAll('td').forEach(c => c.style.outline = '2px solid var(--primary-500)');
          t.querySelectorAll('tr').forEach(r => {
            const td = r.children[idx];
            if (td) td.style.outline = '2px solid var(--primary-500)';
          });
        });
        cell.addEventListener('mouseleave', function() {
          t.querySelectorAll('td').forEach(c => c.style.outline = '');
        });
      });
    }
  },

  // ==========================================================
  // 精灵详情（模态框）
  // ==========================================================
  async _renderPetDetail(name) {
    const data = await DataStore.load();
    const pet = DataStore.pets.find(p => p.name === name);
    if (!pet) {
      this._container.innerHTML = `<div class="empty-state">未找到精灵: ${Utils.esc(name)}</div>`;
      return;
    }

    const elements = (pet.element || []).join(' / ');
    const stats = pet.stats;
    const skills = pet.skills || [];
    const teamRefs = DataStore.petIndex[name] || [];

    let html = `<div class="modal-overlay" onclick="if(event.target===this)Router.go('pets')">
      <div class="modal">`;
    html += `<button class="modal-close" onclick="Router.go('pets')">&times;</button>`;
    const img = pet.image ? `<div class="pet-detail-hero-img"><img src="${Utils.esc(pet.image)}" alt="${Utils.esc(pet.name)}"></div>` : '';
    html += `<h2>${Utils.esc(pet.name)}</h2>${img}
      <div class="subtitle">${Utils.esc(elements)}</div>`;
    if (pet.description) {
      html += `<p style="font-size:13px;color:#666;margin-bottom:16px;">${Utils.esc(pet.description)}</p>`;
    }
    if (stats) {
      html += `<div class="detail-section"><h3>种族值 (总和: ${stats.total||'-'})</h3>
        <div class="stat-row">
          <div class="stat-item"><div class="label">生命</div><div class="value">${stats.hp??'-'}</div></div>
          <div class="stat-item"><div class="label">物攻</div><div class="value">${stats.attack??'-'}</div></div>
          <div class="stat-item"><div class="label">魔攻</div><div class="value">${stats.magic_attack??'-'}</div></div>
          <div class="stat-item"><div class="label">物防</div><div class="value">${stats.defense??'-'}</div></div>
          <div class="stat-item"><div class="label">魔防</div><div class="value">${stats.magic_defense??'-'}</div></div>
          <div class="stat-item"><div class="label">速度</div><div class="value">${stats.speed??'-'}</div></div>
        </div></div>`;
    }
    if (skills.length > 0) {
      html += `<div class="detail-section"><h3>技能列表 (${skills.length} 个)</h3>
        <table class="skill-table"><thead><tr><th>名称</th><th>系别</th><th>分类</th><th>能耗</th><th>威力</th><th>效果</th><th>解锁</th></tr></thead><tbody>`;
      for (const s of skills) {
        html += `<tr><td><strong>${Utils.esc(s.name)}</strong></td>
          <td>${Utils.esc(s.element||'-')}</td>
          <td>${Utils.esc(s.category||'-')}</td>
          <td>${s.cost!=null?s.cost:'-'}</td>
          <td>${s.power!=null?s.power:'-'}</td>
          <td class="skill-effect">${Utils.truncate(s.effect||'',60)}</td>
          <td style="font-size:11px;color:#999">${Utils.truncate(s.source||'',20)}</td></tr>`;
      }
      html += '</tbody></table></div>';
    } else {
      html += '<div class="detail-section"><h3>技能</h3><p style="color:#999">暂无详细技能数据</p></div>';
    }
    if (teamRefs.length > 0) {
      html += `<div class="detail-section"><h3>出现在以下阵容</h3>`;
      for (const ref of teamRefs) {
        html += `<div style="margin:4px 0;font-size:13px;">
          <span class="team-rank ${ref.rank}">${ref.rank}</span>
          <a href="#" onclick="Router.go('teams')" style="color:var(--primary);text-decoration:none;">${Utils.esc(ref.team)}</a>
          <span style="color:#999;font-size:12px;"> (${ref.role})</span>
        </div>`;
      }
      html += `</div>`;
    }
    html += `</div></div>`;
    this._container.innerHTML = html;
    await Utils.sleep(50);
    const overlay = this._container.querySelector('.modal-overlay');
    if (overlay) overlay.style.opacity = '1';
  },

  // ==========================================================
  // 技能数据库
  // ==========================================================
  async _renderSkills() {
    const data = await DataStore.load();
    await this._ensureSkillIndex();

    const allSkills = this._skillIndex?.allSkills || [];
    const byElem = this._skillIndex?.byElement || {};
    const byCat = this._skillIndex?.byCategory || {};
    const skillToPets = this._skillIndex?.skillToPets || {};

    const elem = this._skillFilterElem || '';
    const cat = this._skillFilterCat || '';
    const kw = this._searchKw?.toLowerCase() || '';

    let filtered = allSkills;
    if (elem) filtered = filtered.filter(s => (s.element||'') === elem);
    if (cat) filtered = filtered.filter(s => (s.category||'') === cat);
    if (kw) filtered = filtered.filter(s => s.name.includes(kw) || (s.effect||'').includes(kw));

    const allElements = [...new Set(allSkills.map(s => s.element).filter(Boolean))].sort();
    const allCats = [...new Set(allSkills.map(s => s.category).filter(Boolean))].sort();

    let html = '<div class="page-header"><h2>技能数据库</h2><p>浏览所有技能、查找精灵会什么技能</p></div>';

    // 筛选栏
    html += '<div class="builder-filter-bar"><div class="filter-row">'
      + '<button class="btn-filter'+(!elem?' active':'')+'" onclick="Renderer._skillFilterElem=\'\';Renderer._renderCurrentView()">全部属性</button>'
      + '<select class="filter-select" onchange="Renderer._skillFilterElem=this.value;Renderer._renderCurrentView()">'
      + '<option value="">属性</option>';
    for (const e of allElements) {
      html += '<option value="'+e+'"'+(elem===e?' selected':'')+'>'+e+' ('+((byElem[e]||[]).length)+')</option>';
    }
    html += '</select>'
      + '<select class="filter-select" onchange="Renderer._skillFilterCat=this.value;Renderer._renderCurrentView()">'
      + '<option value="">分类</option>';
    for (const c of allCats) {
      html += '<option value="'+c+'"'+(cat===c?' selected':'')+'>'+c+' ('+((byCat[c]||[]).length)+')</option>';
    }
    html += '</select>'
      + '</div></div>';

    // 使用顶栏搜索框
    this._showSearch(true);
    if (this._searchInput) {
      this._searchInput.value = this._searchKw || '';
      this._searchInput.setAttribute('placeholder', '搜索技能名或效果...');
    }

    // 统计卡片
    html += '<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">'
      + '<span class="card-tag">总计 '+allSkills.length+' 技能</span>'
      + '<span class="card-tag">'+allElements.length+' 种属性</span>'
      + '<span class="card-tag">'+allCats.length+' 种分类</span>'
      + '</div>';

    // 技能表格
    html += '<div style="overflow-x:auto"><table class="skill-table" style="font-size:13px"><thead><tr>'
      + '<th>名称</th><th>属性</th><th>分类</th><th>能耗</th><th>威力</th><th>效果</th><th>使用精灵</th>'
      + '</tr></thead><tbody>';

    for (const s of filtered) {
      const petsWith = skillToPets[s.name] || [];
      const petNames = petsWith.slice(0, 4).map(n => Utils.esc(n)).join(', ');
      const more = petsWith.length > 4 ? `…等${petsWith.length}只` : '';

      html += '<tr class="skill-row">'
        + '<td><strong>'+Utils.esc(s.name)+'</strong></td>'
        + '<td><span class="card-tag" style="background:'+Utils.elementColor(s.element)+';color:#fff">'+Utils.esc(s.element||'-')+'</span></td>'
        + '<td>'+Utils.esc(s.category||'-')+'</td>'
        + '<td>'+(s.cost!=null?s.cost:'-')+'</td>'
        + '<td>'+(s.power!=null?s.power:'-')+'</td>'
        + '<td class="skill-effect" style="max-width:300px">'+Utils.esc((s.effect||'').slice(0,60))+'</td>'
        + '<td style="font-size:12px;color:var(--neutral-500)">'+petNames+'<span style="color:var(--primary-500)">'+more+'</span></td>'
        + '</tr>';
    }

    html += '</tbody></table></div>';
    if (!filtered.length) html += '<div class="empty-state">未找到匹配的技能</div>';

    this._container.innerHTML = html;
  },

  /** 确保技能索引已加载 */
  async _ensureSkillIndex() {
    if (this._skillIndex) return;
    // Build from product data
    const pets = DataStore.pets;
    const skillMap = {};
    const skillToPets = {};

    for (const pet of pets) {
      const pname = pet.name;
      for (const s of (pet.skills||[])) {
        const sname = s.name;
        if (!sname) continue;
        if (!skillMap[sname]) {
          skillMap[sname] = {
            name: sname,
            element: s.element || '',
            category: s.category || '',
            cost: s.cost,
            power: s.power,
            effect: s.effect || '',
          };
        }
        if (!skillToPets[sname]) skillToPets[sname] = [];
        if (!skillToPets[sname].includes(pname)) skillToPets[sname].push(pname);
      }
    }

    const allSkills = Object.values(skillMap);
    const byElement = {};
    const byCategory = {};
    for (const s of allSkills) {
      const e = s.element || '无';
      const c = s.category || '无';
      if (!byElement[e]) byElement[e] = [];
      byElement[e].push(s.name);
      if (!byCategory[c]) byCategory[c] = [];
      byCategory[c].push(s.name);
    }

    this._skillIndex = { allSkills, byElement, byCategory, skillToPets };
  },

  // ==========================================================
  // 属性克制表
  // ==========================================================
  async _renderTypeChart() {
    const data = await DataStore.load();
    const chart = DataStore.typeChart || {};
    const elements = DataStore.elements || [];
    if (!elements.length) {
      this._container.innerHTML = '<div class="empty-state">属性数据未加载</div>';
      return;
    }

    let html = '<div class="page-header"><h2>属性克制表</h2><p>攻击\\防守 · 2=克制 0.5=被抗 1=普通</p></div>';
    html += '<div class="type-chart-wrap"><table class="type-chart-table" id="typeChartTable"><thead><tr><th>攻\\\\守</th>';
    for (const def of elements) {
      html += '<th>' + Utils.esc(def) + '</th>';
    }
    html += '</tr></thead><tbody>';
    for (const atk of elements) {
      html += '<tr><td class="type-label">' + Utils.esc(atk) + '</td>';
      const row = chart[atk] || {};
      for (const def of elements) {
        const mult = row[def] ?? 1.0;
        html += '<td class="' + Utils.typeClass(mult) + '">' + mult + '</td>';
      }
      html += '</tr>';
    }
    html += '</tbody></table></div>';

    html += '<div class="page-header" style="margin-top:24px"><h3>双属性叠乘规则</h3></div>'
      + '<div style="font-size:13px;color:var(--neutral-500);line-height:1.8">'
      + '<p>双属性均克制（双弱）：2 × 2 = <strong style="color:var(--primary-500)">3.0</strong>（洛克王国世界独立设定）</p>'
      + '<p>双属性均抵抗（双抗）：0.5 × 0.5 = <strong style="color:var(--success-500)">0.25</strong></p>'
      + '<p>一克制一抵抗：2 × 0.5 = <strong>1.0</strong>（抵消）</p>'
      + '<p style="margin-top:8px;font-size:12px">愿力属性不参与克制计算</p>'
      + '</div>';

    this._container.innerHTML = html;

    const t = document.getElementById('typeChartTable');
    if (t) {
      t.querySelectorAll('td').forEach(cell => {
        cell.addEventListener('mouseenter', function() {
          const row = this.parentElement;
          const idx = Array.from(row.children).indexOf(this);
          row.querySelectorAll('td').forEach(c => c.style.outline = '2px solid var(--primary-500)');
          t.querySelectorAll('tr').forEach(r => {
            const td = r.children[idx];
            if (td) td.style.outline = '2px solid var(--primary-500)';
          });
        });
        cell.addEventListener('mouseleave', function() {
          t.querySelectorAll('td').forEach(c => c.style.outline = '');
        });
      });
    }
  },

  // ==========================================================
  // 阵容分享页面
  // ==========================================================
  async _renderSharePage() {
    const data = await DataStore.load();
    const petMap = {};
    for (const p of DataStore.pets) petMap[p.name] = p;

    let myId = DeviceID.get();
    let showMine = this._shareShowMine;
    let showFav = this._shareShowFav;
    let kw = (this._searchKw || '').toLowerCase();
    const sortField = this._shareSortBy === 'click' ? 'click_count'
      : this._shareSortBy === 'cover' ? 'attack_count'
      : this._shareSortBy === 'resist' ? 'defense_count'
      : 'created_at';
    const asc = this._shareSortBy === 'old';

    const allTeams = await this._getSharedTeams(sortField);
    if (!allTeams.length) {
      this._container.innerHTML =
        '<div class="page-header"><h2>阵容分享</h2><p>去精灵图鉴配好队后分享你的阵容</p></div>'
        + '<div class="empty-state">暂无分享的阵容<br><br>'
        + '<button class="btn" onclick="Router.go(\'pets\')">去配队</button></div>';
      return;
    }

    // 前端筛选
    let filtered = [];
    if (showFav) {
      // 我的收藏 = 公开阵容中收藏的 + 本地配队器收藏的草稿
      const favIds = this._getFavIds();
      filtered = allTeams.filter(t => favIds.includes(t.id));
      // 加上本地草稿
      const drafts = this._getFavDrafts();
      filtered = [...drafts, ...filtered];
    } else {
      filtered = allTeams;
      if (showMine) {
        filtered = filtered.filter(t => t.user_id === myId);
      }
    }
    if (kw) {
      filtered = filtered.filter(t =>
        (t.pet_names||[]).some(n => n.includes(kw)) ||
        (t.elements||[]).some(e => e.includes(kw)) ||
        (t.description||'').includes(kw)
      );
    }

    let html = '<div class="page-header"><h2>阵容分享</h2>'
      + '<p>查看玩家分享的PVP阵容，找到适合你的队伍'
      + ' <span class="info-icon" title="无需登录，基于浏览器本地标识识别。换电脑/重装/清缓存会导致标识丢失，无法管理旧阵容。">i</span>'
      + '</p></div>';

    // 标签栏
    html += '<div class="filter-row" style="margin-bottom:4px">'
      + '<button class="btn-filter'+(showFav?'':' active')+'" onclick="Renderer._shareShowMine=false;Renderer._shareShowFav=false;Renderer._renderCurrentView()">全部阵容</button>'
      + '<button class="btn-filter'+(showMine?' active':'')+'" onclick="Renderer._shareShowMine=true;Renderer._shareShowFav=false;Renderer._renderCurrentView()">👤 我的阵容</button>'
      + '<button class="btn-filter'+(showFav?' active':'')+'" onclick="Renderer._shareShowMine=false;Renderer._shareShowFav=true;Renderer._renderCurrentView()">⭐ 我的收藏</button>'
      + '</div>'
      + '<div style="font-size:11px;color:var(--neutral-500);margin-bottom:12px;line-height:1.5">'
      + '「我的阵容」基于浏览器本地标识识别，无需登录。「我的收藏」基于浏览器本地存储(收藏阵容ID+配队器草稿)，清除浏览器缓存会丢失收藏数据，但不影响已发布的阵容。如需修改已发布的阵容，可记下阵容ID联系开发者。'
      + '</div>';

    // 使用顶栏搜索框
    this._showSearch(true);
    if (this._searchInput) {
      this._searchInput.value = this._searchKw || '';
      this._searchInput.setAttribute('placeholder', '搜索精灵名...');
    }

    html += '<div class="share-toolbar" style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;align-items:center">'
      + '<select class="filter-select" onchange="Renderer._shareSortBy=this.value;Renderer._renderCurrentView()">'
      + '<option value="new"'+(this._shareSortBy==='new'?' selected':'')+'>最新</option>'
      + '<option value="old"'+(this._shareSortBy==='old'?' selected':'')+'>最早</option>'
      + '<option value="click"'+(this._shareSortBy==='click'?' selected':'')+'>最热(点击)</option>'
      + '<option value="cover"'+(this._shareSortBy==='cover'?' selected':'')+'>打击面最多</option>'
      + '<option value="resist"'+(this._shareSortBy==='resist'?' selected':'')+'>抵抗面最多</option>'
      + '</select>'
      + '<span style="font-size:13px;color:var(--neutral-500)">'+(showMine?'我的':'共 ')+filtered.length+' 套</span>'
      + '</div>';

    // 我的阵容提示
    if (showMine && !filtered.length) {
      html += '<div class="empty-state">你还没发布过阵容<br><br><button class="btn" onclick="Router.go(\'pets\')">去配队</button></div>';
      this._container.innerHTML = html;
      return;
    }

    html += '<div class="share-grid">';
    for (const entry of filtered) {
      const pets = (entry.pet_names||[]).map(n => petMap[n]).filter(Boolean);
      const coverPct = entry.total_elements ? Math.round((entry.attack_count||0) / entry.total_elements * 100) : 0;
      const resistPct = entry.total_elements ? Math.round((entry.defense_count||0) / entry.total_elements * 100) : 0;
      const timeAgo = this._timeAgo(entry.created_at);
      const isMine = entry.user_id === myId;

      const isFav = this._isFav(entry.id);
      html += '<div class="share-card'+(isMine?' share-card-mine':'')+'" onclick="Renderer._clickSharedTeam('+entry.id+')" style="position:relative">'
        + '<span class="fav-star'+(isFav?' on':'')+'" onclick="event.stopPropagation();Renderer._toggleFav('+entry.id+')">'+(isFav?'★':'☆')+'</span>'
        + (entry.team_name ? '<div class="share-team-name">'+Utils.esc(entry.team_name)+'</div>' : '')
        + '<div class="share-card-header"><div class="share-pet-grid">'
        + '<div class="share-pet-row3">';
      for (let i = 0; i < 3 && i < pets.length; i++) {
        const p = pets[i];
        html += '<div class="share-pet-mini" title="'+Utils.esc(p?.name||'')+'">'
          + (p?.image ? '<img src="'+Utils.esc(p.image)+'" alt="">' : '<span class="share-pet-initial">'+Utils.esc((p?.name||'?')[0])+'</span>')
          + '<span>'+Utils.truncate(p?.name||'',4)+'</span>'
          + '</div>';
      }
      html += '</div>'
        + '<div class="share-pet-row3">';
      for (let i = 3; i < 6 && i < pets.length; i++) {
        const p = pets[i];
        html += '<div class="share-pet-mini" title="'+Utils.esc(p?.name||'')+'">'
          + (p?.image ? '<img src="'+Utils.esc(p.image)+'" alt="">' : '<span class="share-pet-initial">'+Utils.esc((p?.name||'?')[0])+'</span>')
          + '<span>'+Utils.truncate(p?.name||'',4)+'</span>'
          + '</div>';
      }
      html += '</div></div></div>'
      if (entry.description) {
        html += '<div class="share-desc">'+Utils.esc(entry.description)+'</div>';
      }
      html += '<div class="share-stats">'
        + '<span class="share-stat" title="打击面覆盖">⚔ '+coverPct+'%</span>'
        + '<span class="share-stat" title="抵抗面覆盖">🛡 '+resistPct+'%</span>'
        + '<span class="share-stat" title="查看次数">👁 '+(entry.click_count||0)+'</span>'
        + '<span class="share-stat" title="分享时间">🕐 '+timeAgo+'</span>'
        + '<span class="share-stat" style="font-size:9px;color:var(--neutral-500);font-weight:600">#'+entry.id+'</span>'
        + '</div>';
      const hasSkills = Object.keys(entry.skills||{}).length > 0;
      if (hasSkills) {
        html += '<div class="share-skills-preview">';
        for (let i = 0; i < 6; i++) {
          const sk = entry.skills?.[i];
          if (sk && sk.length) {
            html += '<div style="font-size:11px;color:var(--neutral-500)">'
              + Utils.truncate(pets[i]?.name||'?',3)+': '+sk.join(', ')+'</div>';
          }
        }
        html += '</div>';
      }
      if (isMine && showMine) {
        html += '<div style="display:flex;gap:6px;margin-top:6px">'
          + '<button class="btn-sm" style="background:var(--danger-500)" onclick="event.stopPropagation();Renderer._deleteMyTeam('+entry.id+')">🗑 删除</button>'
          + '</div>';
      }
      if (showFav && entry._isDraft) {
        html += '<div style="display:flex;gap:6px;margin-top:6px">'
          + '<button class="btn-sm" style="background:var(--danger-500)" onclick="event.stopPropagation();Renderer._deleteFavDraft(\''+entry.id+'\')">🗑 删除</button>'
          + '</div>';
      }
      html += '</div>';
    }
    html += '</div>';
    if (!filtered.length) html += '<div class="empty-state">未找到匹配的阵容</div>';

    this._container.innerHTML = html;
  },

  // ==========================================================
  // 其他页面
  // ==========================================================
  _renderOtherPage() {
    const html = '<div class="page-header"><h2>其他</h2></div>'
      + '<div class="other-grid">'

      // 意见反馈
      + '<div class="other-card">'
      + '<div class="other-icon">💬</div>'
      + '<h3>意见反馈</h3>'
      + '<p>发现Bug？有功能建议？欢迎告诉我</p>'
      + '<div class="other-contact-row">'
      + '<span class="other-badge">反馈方式</span>'
      + '</div>'
      + '<div class="other-contact-links">'
      + '<a href="https://github.com/your-username/roco-pvp/issues/new" target="_blank" class="other-link">🐛 GitHub Issues</a>'
      + '<span class="other-link disabled" onclick="Renderer._copyText(\'alatus19256@163.com\')">📧 alatus19256@163.com 点击复制</span>'
      + '</div>'
      + '</div>'

      // 联系开发者
      + '<div class="other-card">'
      + '<div class="other-icon">👨‍💻</div>'
      + '<h3>联系开发者</h3>'
      + '<p>关于项目的任何问题都可以联系我</p>'
      + '<div class="other-contact-row">'
      + '<span class="other-badge">联系方式</span>'
      + '</div>'
      + '<div class="other-contact-links">'
      + '<span class="other-link" onclick="Renderer._copyText(\'alatus19256@163.com\')">📧 邮箱: alatus19256@163.com 点击复制</span>'
      + '<span class="other-link" onclick="Renderer._copyText(\'@luoke_pvp\')">🐦 社交: @luoke_pvp 点击复制</span>'
      + '</div>'
      + '</div>'

      // 请开发者喝咖啡
      + '<div class="other-card other-card-coffee">'
      + '<div class="other-icon">☕</div>'
      + '<h3>送开发者一杯咖啡</h3>'
      + '<p>如果你觉得这个工具有帮助，可以请我喝杯咖啡 ☕ 支持持续更新</p>'
      + '<div class="other-coffee-area">'
      + '<img src="data/pay-good.jpg" style="width:160px;height:160px;object-fit:contain;border-radius:12px" alt="赞赏码">'
      + '<p style="font-size:12px;color:var(--neutral-500);margin-top:8px">赞赏支持，感谢 ☕</p>'
      + '</div>'
      + '</div>'

      // 项目信息
      + '<div class="other-card">'
      + '<div class="other-icon">ℹ️</div>'
      + '<h3>关于项目</h3>'
      + '<div class="other-info">'
      + '<div class="other-info-row"><span>项目名称</span><span>洛克王国世界PVP助手</span></div>'
      + '<div class="other-info-row"><span>版本</span><span>1.0.0</span></div>'
      + '<div class="other-info-row"><span>数据源</span><span>BiliWiki · 社区攻略</span></div>'
      + '<div class="other-info-row"><span>精灵总数</span><span>'+(DataStore.pets?.length||'...')+' 只</span></div>'
      + '</div>'
      + '</div>'

      + '</div>';

    this._container.innerHTML = html;
  },

  _copyText(text) {
    navigator.clipboard?.writeText(text).then(() => {
      alert('已复制: ' + text);
    }).catch(() => {
      prompt('复制以下内容:', text);
    });
  },

  // ============================================================
  // 收藏功能
  // ============================================================
  _getFavIds() {
    try { return JSON.parse(localStorage.getItem('pvp_fav_ids') || '[]'); }
    catch { return []; }
  },
  _saveFavIds(ids) { localStorage.setItem('pvp_fav_ids', JSON.stringify(ids)); },

  _isFav(id) { return this._getFavIds().includes(id); },

  _toggleFav(id) {
    let ids = this._getFavIds();
    if (ids.includes(id)) { ids = ids.filter(i => i !== id); }
    else { ids.push(id); }
    this._saveFavIds(ids);
    this._renderCurrentView();
  },

  /** 收藏配队器结果（存本地，不进公开池） */
  _favTeamFromBuilder() {
    if (this._team.length === 0) { alert('请先配队'); return; }
    const entry = {
      id: 'fav_' + Date.now(),
      team_name: '收藏队伍',
      pet_names: this._team.map(p => p.name),
      elements: [...new Set(this._team.flatMap(p => p.element||[]))],
      skills: {}, natures: {}, wills: {}, stats: {},
      description: '来自配队器的收藏',
      created_at: new Date().toISOString(),
      _isDraft: true,
    };
    for (let i = 0; i < 6; i++) {
      const sk = (this._teamSkills[i]||[]).filter(Boolean).map(s => s.name);
      entry.skills[i] = sk;
      if (this._petNature[i]) entry.natures[i] = this._petNature[i];
      if (this._teamWill[i]) entry.wills[i] = this._teamWill[i];
      if (this._teamStats[i]?.length) entry.stats[i] = this._teamStats[i];
    }
    let drafts = this._getFavDrafts();
    drafts.unshift(entry);
    this._saveFavDrafts(drafts);
    alert('✅ 已收藏到「我的收藏」');
  },

  _getFavDrafts() {
    try { return JSON.parse(localStorage.getItem('pvp_fav_drafts') || '[]'); }
    catch { return []; }
  },
  _saveFavDrafts(d) { localStorage.setItem('pvp_fav_drafts', JSON.stringify(d)); },
  _deleteFavDraft(id) {
    let d = this._getFavDrafts();
    this._saveFavDrafts(d.filter(e => e.id !== id));
    this._renderCurrentView();
  },

  /** 删除我的阵容 */
  async _deleteMyTeam(id) {
    if (!confirm('确定删除这条阵容？')) return;
    const ok = await SupabaseDB.deleteTeam(id, DeviceID.get());
    if (ok) {
      alert('✅ 已删除');
      this._renderCurrentView();
    } else {
      alert('⚠️ 删除失败，可能不是你的阵容');
    }
  },

  /** 点击阵容：记录+1（云端） */
  async _clickSharedTeam(id) {
    await SupabaseDB.clickTeam(id);
    this._showSharedTeamDetail(id);
  },

  /** 从分享阵容导入到配队器 */
  async _importTeamToBuilder(id) {
    const teams = await this._getSharedTeams('created_at');
    const entry = teams.find(t => t.id === id);
    if (!entry) return;

    const pets = DataStore.pets;
    const names = entry.pet_names || [];
    this._team = names.map(n => pets.find(p => p.name === n)).filter(Boolean);
    this._teamSkills = {};
    this._teamWill = {};
    this._teamLeader = {};
    this._petNature = {};
    this._teamStats = {};
    this._builderCollapsed = false;
    this._selectedSlot = null;

    // 恢复配招/性格/愿力
    for (let i = 0; i < this._team.length; i++) {
      const sk = entry.skills?.[i] || [];
      const petSkills = this._team[i]?.skills || [];
      this._teamSkills[i] = sk.map(sname => petSkills.find(s => s.name === sname)).filter(Boolean);
      while (this._teamSkills[i].length < 4) this._teamSkills[i].push(null);
      if (entry.natures?.[i]) this._petNature[i] = entry.natures[i];
      if (entry.wills?.[i]) this._teamWill[i] = entry.wills[i];
      if (entry.stats?.[i]) this._teamStats[i] = entry.stats[i];
    }

    this._saveTeamSnapshot();
    Router.go('pets');
    this._renderCurrentView();
  },

  /** 显示分享阵容详情弹窗 */
  async _showSharedTeamDetail(id) {
    const teams = await this._getSharedTeams('created_at');
    const entry = teams.find(t => t.id === id);
    if (!entry) return;

    const petMap = {};
    for (const p of DataStore.pets) petMap[p.name] = p;
    const pets = (entry.pet_names||[]).map(n => petMap[n]).filter(Boolean);

    // 移除旧弹窗
    const old = document.getElementById('shareDetail');
    if (old) old.remove();

    const div = document.createElement('div');
    div.id = 'shareDetail';
    div.className = 'share-detail-overlay';
    div.onclick = function(e) { if (e.target === this) this.remove(); };

    let inner = '<div class="share-detail-panel">'
      + '<button class="share-detail-close" onclick="this.closest(\'.share-detail-overlay\').remove()">×</button>'
      + '<h3>分享阵容详情</h3>';

    if (entry.description) {
      inner += '<p style="color:var(--neutral-500);font-size:13px;margin-bottom:12px">'+Utils.esc(entry.description)+'</p>';
    }

    inner += '<div class="share-detail-elems">'+(entry.elements||[]).map(e => '<span class="card-tag" style="background:'+Utils.elementColor(e)+';color:#fff">'+e+'</span>').join('')+'</div>';

    const coverPct = entry.total_elements ? Math.round((entry.attack_count||0)/entry.total_elements*100) : 0;
    const resistPct = entry.total_elements ? Math.round((entry.defense_count||0)/entry.total_elements*100) : 0;
    inner += '<div style="font-size:12px;color:var(--neutral-500);margin:8px 0">'
      + '打击面 '+coverPct+'% ｜ 抵抗面 '+resistPct+'% ｜ 👁 '+(entry.click_count||0)+' 次查看</div>'
      + '<div style="font-size:10px;color:var(--neutral-500);font-weight:600;text-align:right;margin-top:-4px">ID: '+entry.id+'</div>';

    inner += '<div class="share-detail-pets">';
    for (let i = 0; i < (entry.pet_names||[]).length; i++) {
      const p = pets[i];
      const skillsList = entry.skills?.[i] || [];
      const nature = entry.natures?.[i] || '';
      const will = entry.wills?.[i] || '';

      inner += '<div class="share-detail-pet">'
        + (p?.image ? '<img src="'+Utils.esc(p.image)+'" class="share-detail-img">' : '')
        + '<div><strong>'+Utils.esc(entry.pet_names[i])+'</strong>'
        + (nature ? ' ['+nature+']' : '')
        + (will ? ' 愿力:'+will : '')
        + '<div style="font-size:12px;color:var(--neutral-500);margin-top:4px">'
        + (skillsList.length ? '技能: '+skillsList.join(' → ') : '无配招')
        + '</div></div></div>';
    }
    inner += '</div>'
      + '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">'
      + '<button class="btn-filter" onclick="Renderer._importTeamToBuilder('+entry.id+');this.closest(\'.share-detail-overlay\').remove()">📥 导入配队器</button>'
      + '<button class="btn" onclick="this.closest(\'.share-detail-overlay\').remove()">关闭</button>'
      + '</div></div>';

    div.innerHTML = inner;
    document.body.appendChild(div);
  },

  /** 时间友好显示 */
  _timeAgo(isoStr) {
    if (!isoStr) return '';
    const now = Date.now();
    const t = new Date(isoStr).getTime();
    const diff = Math.floor((now - t) / 1000);
    if (diff < 60) return '刚刚';
    if (diff < 3600) return Math.floor(diff/60)+'分钟前';
    if (diff < 86400) return Math.floor(diff/3600)+'小时前';
    return Math.floor(diff/86400)+'天前';
  },

  // ==========================================================
  // 配队构建器核心方法
  // ==========================================================
  _addToTeam(name) {
    if (this._team.length >= 6) return;
    const pet = DataStore._data?.pets.find(p => p.name === name);
    if (pet && !this._team.find(p => p.name === name)) {
      this._team.push(pet);
      const idx = this._team.length - 1;
      this._teamSkills[idx] = [null, null, null, null];
      this._teamWill[idx] = '';
      this._teamLeader[idx] = false;
      this._petNature[idx] = '';
      this._teamStats[idx] = [];
      this._selectedSlot = null;
      this._saveTeamSnapshot();
      this._renderCurrentView();
    }
  },

  _removeFromTeam(i) {
    this._team.splice(i,1);
    delete this._teamSkills[i];
    delete this._teamWill[i];
    delete this._teamLeader[i];
    delete this._petNature[i];
    delete this._teamStats[i];
    for (const key of ['_teamSkills', '_teamWill', '_teamLeader', '_petNature']) {
      const reindexed = {};
      for (const k of Object.keys(this[key])) {
        const newIdx = parseInt(k) > i ? parseInt(k) - 1 : parseInt(k);
        reindexed[newIdx] = this[key][k];
      }
      this[key] = reindexed;
    }
    this._selectedSlot = null;
    this._saveTeamSnapshot();
    this._renderCurrentView();
  },

  /** 自动保存队伍快照到 localStorage */
  /** 渲染可点击的种族值项 */
  _statItem(petIdx, st, key, label) {
    const selected = this._teamStats[petIdx] || [];
    const isSel = selected.includes(key);
    const val = st[key] ?? '-';
    const cls = isSel ? 'sd-stat-item sel' : 'sd-stat-item';
    return '<div class="'+cls+'" onclick="Renderer._toggleStat('+petIdx+',\''+key+'\')"><span class="sd-stat-label">'+label+'</span><span class="sd-stat-val">'+val+'</span></div>';
  },

  /** 切换种族值选中（最多3个） */
  _toggleStat(petIdx, key) {
    if (!this._teamStats[petIdx]) this._teamStats[petIdx] = [];
    const selected = this._teamStats[petIdx];
    const idx = selected.indexOf(key);
    if (idx >= 0) {
      selected.splice(idx, 1);  // 取消选中
    } else {
      if (selected.length >= 3) return;  // 最多3个
      selected.push(key);
    }
    this._saveTeamSnapshot();
    this._renderCurrentView();
  },

  /** 计算攻击属性对某个精灵的最终克制倍率（支持双属性） */
  _calcEffectiveness(atk, pet) {
    const chart = DataStore.typeChart || {};
    const elements = pet.element || [];
    if (!elements.length) return 1.0;
    let mult = 1.0;
    for (const def of elements) {
      mult *= (chart[atk]||{})[def] || 1.0;
    }
    // 洛克王国世界特殊规则：双属性均克制 = 3.0 而不是 4.0
    if (elements.length === 2) {
      const each = elements.map(def => (chart[atk]||{})[def] || 1.0);
      if (each[0] >= 2 && each[1] >= 2) mult = 3.0;
    }
    return mult;
  },

  /** 判断队伍是否完整（6只精灵+每只4技能全满） */
  _isTeamComplete() {
    if (this._team.length !== 6) return false;
    for (let i = 0; i < 6; i++) {
      const skills = this._teamSkills[i] || [null, null, null, null];
      if (skills.filter(Boolean).length < 4) return false;
    }
    return true;
  },

  /** 计算队伍打击面/抵抗面数 */
  _calcTeamCoverage() {
    const chart = DataStore.typeChart || {};
    const allElems = DataStore.elements || [];
    const teamElems = [];
    for (const p of this._team) {
      for (const e of (p.element || [])) {
        if (!teamElems.includes(e)) teamElems.push(e);
      }
    }
    // 打击面（攻击方能克制多少防御属性）
    const cover = {};
    for (const atk of teamElems) {
      for (const def of allElems) {
        if ((chart[atk]||{})[def] >= 2) cover[def] = true;
      }
    }
    // 抵抗面（防御方能抵抗多少攻击属性—双重及以上）
    const resist = {};
    for (const p of this._team) {
      for (const atk of allElems) {
        const eff = this._calcEffectiveness(atk, p);
        if (eff <= 0.5) resist[atk] = true;
      }
    }
    return {
      attackCount: Object.keys(cover).length,
      defenseCount: Object.keys(resist).length,
      totalElements: allElems.length,
    };
  },

  /** 获取所有分享阵容（从Supabase） */
  async _getSharedTeams(sortBy) {
    try { return await SupabaseDB.getTeams(sortBy); }
    catch { return []; }
  },

  /** 打开分享弹窗 */
  _openShareDialog() {
    if (!this._isTeamComplete()) {
      alert('请先填满6只精灵并给每只配好4个技能');
      return;
    }
    const old = document.getElementById('shareDialog');
    if (old) old.remove();

    const coverage = this._calcTeamCoverage();
    const savedName = localStorage.getItem('pvp_team_draft_name') || '';
    const savedDesc = localStorage.getItem('pvp_team_draft_desc') || '';

    // 构建6只精灵的卡片HTML
    let petsHtml = '';
    for (let i = 0; i < 6; i++) {
      const p = this._team[i];
      if (!p) continue;
      const elTags = (p.element||[]).map(e => '<span class="card-tag" style="background:'+Utils.elementColor(e)+';color:#fff;font-size:9px">'+e+'</span>').join('');
      const skills = this._teamSkills[i] || [null,null,null,null];
      const skillHtml = skills.map(s => s ? '<span style="font-size:10px;padding:1px 4px;background:var(--primary-50);border-radius:4px">'+Utils.esc(s.name)+'</span>' : '<span style="font-size:10px;color:var(--neutral-200)">—</span>').join('');

      petsHtml += '<div class="share-card-pet" onclick="Renderer._showSlotDetail('+i+');document.getElementById(\'shareDialog\').remove()">'
        + (p.image ? '<img src="'+Utils.esc(p.image)+'" style="width:48px;height:48px;object-fit:contain;border-radius:6px;background:var(--neutral-50)">' : '')
        + '<div style="flex:1;min-width:0">'
        + '<div style="font-size:13px;font-weight:600">'+Utils.esc(p.name)+'</div>'
        + '<div style="font-size:10px;color:var(--neutral-500)">'+elTags+'</div>'
        + '<div style="display:flex;gap:2px;margin-top:2px;flex-wrap:wrap">'+skillHtml+'</div>'
        + '</div></div>';
    }

    const coverPct = coverage.totalElements ? Math.round(coverage.attackCount/coverage.totalElements*100) : 0;
    const resistPct = coverage.totalElements ? Math.round(coverage.defenseCount/coverage.totalElements*100) : 0;

    const div = document.createElement('div');
    div.id = 'shareDialog';
    div.className = 'share-dialog-overlay';
    div.innerHTML = '<div class="share-card-dialog">'
      + '<div class="share-card-section">'
      + '<input id="shareTeamName" class="share-name-input" placeholder="队伍名（选填，最多15字）" maxlength="15" value="'+Utils.esc(savedName)+'">'
      + '</div>'
      + '<div class="share-card-section share-card-pets">'
      + '<div style="font-size:11px;color:var(--neutral-500);margin-bottom:6px">点击精灵可修改配招</div>'
      + petsHtml
      + '</div>'
      + '<div class="share-card-section">'
      + '<div style="font-size:12px;color:var(--neutral-500);margin-bottom:4px">打击面 '+coverPct+'% ｜ 抵抗面 '+resistPct+'%</div>'
      + '<textarea id="shareDesc" class="share-desc-input" placeholder="队伍描述：玩法思路、适用段位、克制关系等">'+Utils.esc(savedDesc)+'</textarea>'
      + '</div>'
      + '<div class="share-card-section share-card-actions">'
      + '<button class="btn-filter" onclick="Renderer._saveShareDraft()">💾 保存草稿</button>'
      + '<button class="btn" onclick="Renderer._doShareTeam()">📤 确认分享</button>'
      + '</div></div>';
    document.body.appendChild(div);
  },

  /** 保存草稿 */
  _saveShareDraft() {
    const nameEl = document.getElementById('shareTeamName');
    const descEl = document.getElementById('shareDesc');
    localStorage.setItem('pvp_team_draft_name', nameEl?.value || '');
    localStorage.setItem('pvp_team_draft_desc', descEl?.value || '');
    alert('✅ 草稿已保存');
  },

  async _doShareTeam() {
    if (!this._isTeamComplete()) return;
    const nameEl = document.getElementById('shareTeamName');
    const descEl = document.getElementById('shareDesc');
    const teamName = nameEl ? nameEl.value.trim() : '';
    const description = descEl ? descEl.value.trim() : '';
    const coverage = this._calcTeamCoverage();

    const entry = {
      user_id: DeviceID.get(),
      team_name: teamName || null,
      pet_names: this._team.map(p => p.name),
      elements: [...new Set(this._team.flatMap(p => p.element||[]))],
      skills: {},
      natures: {},
      wills: {},
      description,
      attack_count: coverage.attackCount,
      defense_count: coverage.defenseCount,
      total_elements: coverage.totalElements,
    };

    for (let i = 0; i < 6; i++) {
      const skills = (this._teamSkills[i]||[]).filter(Boolean).map(s => s.name);
      entry.skills[i] = skills;
      if (this._petNature[i]) entry.natures[i] = this._petNature[i];
      if (this._teamWill[i]) entry.wills[i] = this._teamWill[i];
      if (this._teamStats[i]?.length) entry.stats = entry.stats || {};
      if (this._teamStats[i]?.length) entry.stats[i] = this._teamStats[i];
    }

    const result = await SupabaseDB.publishTeam(entry);
    const dialog = document.getElementById('shareDialog');
    if (dialog) dialog.remove();

    // 清除草稿
    localStorage.removeItem('pvp_team_draft_name');
    localStorage.removeItem('pvp_team_draft_desc');
    if (result) {
      alert('✅ 阵容已发布到云端！所有用户可见');
    } else {
      alert('⚠️ 发布失败，请检查网络后重试');
    }
  },

  _saveTeamSnapshot() {
    try {
      const snapshot = {
        names: this._team.map(p => p.name),
        will: Object.fromEntries(Object.entries(this._teamWill).filter(([k,v]) => v)),
        leader: Object.fromEntries(Object.entries(this._teamLeader).filter(([k,v]) => v)),
        nature: Object.fromEntries(Object.entries(this._petNature).filter(([k,v]) => v)),
        stats: Object.fromEntries(Object.entries(this._teamStats).filter(([k,v]) => v && v.length)),
        savedAt: Date.now(),
      };
      localStorage.setItem('pvp_team_snapshot', JSON.stringify(snapshot));
    } catch (_) { /* ignore */ }
  },

  /** 从 localStorage 恢复队伍快照 */
  _loadTeamSnapshot() {
    try {
      const raw = localStorage.getItem('pvp_team_snapshot');
      if (!raw) return;
      const snap = JSON.parse(raw);
      if (!snap.names || !snap.names.length) return;
      const pets = DataStore.pets;
      this._team = snap.names.map(n => pets.find(p => p.name === n)).filter(Boolean);
      this._teamSkills = {};
      this._teamWill = snap.will || {};
      this._teamLeader = snap.leader || {};
      this._petNature = snap.nature || {};
      this._teamStats = snap.stats || {};
      this._team.forEach((_, i) => {
        if (!this._teamSkills[i]) this._teamSkills[i] = [null, null, null, null];
      });
    } catch (_) { /* ignore */ }
  },

  _clearTeam() {
    this._team = []; this._teamSkills = {};
    this._teamWill = {}; this._teamLeader = {};
    this._petNature = {}; this._teamStats = {}; this._selectedSlot = null;
    this._saveTeamSnapshot();
    this._renderCurrentView();
  },

  /** 队伍导出为文本 */
  _exportTeam() {
    if (!this._team.length) return;
    const elements = [...new Set(this._team.flatMap(p => p.element||[]))];
    const totalStats = this._team.reduce((s, p) => {
      const st = p.stats||{};
      return {hp: s.hp+(st.hp||0), atk: s.atk+(st.attack||0)+ (st.magic_attack||0), def: s.def+(st.defense||0)+(st.magic_defense||0), spd: s.spd+(st.speed||0)};
    }, {hp:0, atk:0, def:0, spd:0});
    const lines = this._team.map((p, i) => {
      const skills = (this._teamSkills[i]||[]).filter(Boolean).map(s => s.name).join(', ');
      const nature = this._petNature[i] || '';
      const will = this._teamWill[i] || '';
      const stats = p.stats||{};
      return `${i+1}. ${p.name}${nature?' ['+nature+']':''}${will?' 愿力:'+will:''}${skills?' 技能: '+skills:''} (${(stats.total||'?')}种族)`;
    });
    const text = '=== 洛克王国世界PVP队伍 ===\n' + lines.join('\n')
      + `\n---\n属性: ${elements.join('/')} | 种族: HP${totalStats.hp} 攻${totalStats.atk} 防${totalStats.def} 速${totalStats.spd}`;
    navigator.clipboard?.writeText(text).catch(()=>{});
    prompt('队伍信息已复制:', text);
  },

  _showSlotDetail(i) {
    this._selectedSlot = this._selectedSlot === i ? null : i;
    this._renderCurrentView();
  },

  _hideSlotDetail() {
    this._selectedSlot = null;
    this._renderCurrentView();
  },

  _assignTeamSkillAuto(petIdx) {
    const skills = this._team[petIdx]?.skills || [];
    const selected = this._teamSkills[petIdx] || [null, null, null, null];
    const firstEmpty = selected.indexOf(null);
    if (firstEmpty < 0) return;
    const usedNames = new Set(selected.filter(s => s).map(s => s.name));
    for (const sk of skills) {
      if (!usedNames.has(sk.name)) {
        selected[firstEmpty] = sk;
        this._teamSkills[petIdx] = selected;
        this._saveTeamSnapshot();
        this._renderCurrentView();
        return;
      }
    }
  },

  _assignTeamSkill(petIdx, skillName) {
    const skills = this._team[petIdx]?.skills || [];
    const sk = skills.find(s => s.name === skillName);
    if (!sk) return;
    const selected = this._teamSkills[petIdx] || [null, null, null, null];
    const firstEmpty = selected.indexOf(null);
    if (firstEmpty < 0) return;
    selected[firstEmpty] = sk;
    this._teamSkills[petIdx] = selected;
    this._saveTeamSnapshot();
    this._renderCurrentView();
  },

  _removeTeamSkill(petIdx, slotIdx) {
    const selected = this._teamSkills[petIdx];
    if (!selected) return;
    selected[slotIdx] = null;
    this._teamSkills[petIdx] = selected;
    this._saveTeamSnapshot();
    this._renderCurrentView();
  },

  /** 去除精灵名中的括号标注词，如 "魔力猫（首领形态）" → "魔力猫" */
  _stripNameSuffix(name) {
    return name.replace(/[（(][^）)]*[）)]/g, '').trim();
  },

  _buildLeaderMap() {
    if (this._leaderMap && Object.keys(this._leaderMap).length > 0) return;
    this._leaderMap = this._leaderMap || {};
    if (!DataStore._data) return;
    const pets = DataStore.pets;

    // 第一遍：标准首领映射
    for (const p of pets) {
      const n = p.name;
      const m = n.match(/^(.+)（首领形态[^）]*）/);
      if (m) { this._leaderMap[m[1]] = n; continue; }
      if (n.startsWith('首领化')) { this._leaderMap[n.slice(3)] = n; }
    }

    // 第二遍：带括号标注的精灵映射到同名基础精灵的首领
    for (const p of pets) {
      const base = this._stripNameSuffix(p.name);
      if (base !== p.name && this._leaderMap[base]) {
        this._leaderMap[p.name] = this._leaderMap[base];
      }
    }

    // 第三遍：特殊关联——首领名与同首字精灵共享
    // 例："棋契陛下（首领形态）" 关联所有"棋X"精灵（排除同名双字"棋棋"）
    for (const p of pets) {
      const m = p.name.match(/^(.+)（首领形态[^）]*）/);
      if (!m) continue;
      const leaderBase = m[1];
      const prefix = leaderBase[0];
      if (!prefix || leaderBase.length < 2) continue;
      for (const p2 of pets) {
        const n2 = p2.name;
        if (n2 === p.name || this._leaderMap[n2]) continue;
        const core2 = this._stripNameSuffix(n2);
        // 核心名以首领首字开头（如"棋"），排除"棋棋"这种双字重复
        if (core2.startsWith(prefix) && core2 !== leaderBase && core2 !== prefix + prefix) {
          this._leaderMap[n2] = p.name;
        }
      }
    }
  },

  /** 查询精灵的首领形态名，支持括号标注词匹配 */
  _getLeaderName(name) {
    this._buildLeaderMap();
    if (!this._leaderMap) return null;
    // 精确匹配优先
    if (this._leaderMap[name]) return this._leaderMap[name];
    // 去掉括号标注再匹配
    const base = this._stripNameSuffix(name);
    if (base !== name && this._leaderMap[base]) return this._leaderMap[base];
    return null;
  },

  _toggleLeader(slotIdx) {
    this._teamLeader[slotIdx] = !this._teamLeader[slotIdx];
    this._renderCurrentView();
  },

  _switchToLeader(slotIdx) {
    const current = this._team[slotIdx];
    if (!current) return;
    const leaderName = this._getLeaderName(current.name);
    if (!leaderName) return;
    const leaderPet = DataStore._data?.pets.find(p => p.name === leaderName);
    if (leaderPet) {
      this._team[slotIdx] = leaderPet;
      this._teamLeader[slotIdx] = true;
      this._renderCurrentView();
    }
  },

  _getSavedTeams() {
    try { return JSON.parse(localStorage.getItem('pvp_teams') || '[]'); }
    catch { return []; }
  },

  _saveTeamsToStorage(t) {
    localStorage.setItem('pvp_teams', JSON.stringify(t));
  },

  _elementColor(elem) { return Utils.elementColor(elem); },

  _expandPetCard(name) {
    const pets = DataStore.pets;
    for (let i = 0; i < pets.length; i++) {
      if (pets[i].name === name) {
        this._expandedPet = { idx: i, name };
        this._renderCurrentView();
        return;
      }
    }
  },

  _collapsePetCard() {
    this._expandedPet = null;
    this._renderCurrentView();
  },

  _dragSkillStart(e, petIdx, si) {
    this._dragSkillData = { petIdx, si };
    e.dataTransfer.effectAllowed = 'move';
  },

  _dragSkillDrop(e, petIdx, si) {
    e.preventDefault();
    if (!this._dragSkillData || this._dragSkillData.petIdx !== petIdx) return;
    const skills = this._teamSkills[petIdx] || [null, null, null, null];
    const from = this._dragSkillData.si;
    if (from === si) return;
    const fromSkill = skills[from];
    const toSkill = skills[si];
    skills[from] = toSkill;
    skills[si] = fromSkill;
    this._teamSkills[petIdx] = skills;
    this._renderCurrentView();
    this._dragSkillData = null;
  },

  _dragSlotStart(e, idx) { this._dragSlotIdx = idx; e.dataTransfer.effectAllowed = 'move'; },

  _dragSlotDrop(e, idx) {
    e.preventDefault();
    const from = this._dragSlotIdx;
    if (from === null || from === idx) return;
    const pet = this._team.splice(from, 1)[0];
    this._team.splice(idx, 0, pet);
    this._renderCurrentView();
    this._dragSlotIdx = null;
  },

  _toggleSortSpeed() {
    this._petSortBy = this._petSortBy === 'speed' ? null : 'speed';
    this._renderCurrentView();
  },

  _typeTooltip(elem, mode) {
    if (!DataStore._data) return '';
    const chart = DataStore.typeChart || {};
    const allElems = DataStore.elements || [];
    const attackRow = chart[elem] || {};
    const strong = allElems.filter(e => attackRow[e] >= 2);       // 攻击克制
    const resisted = allElems.filter(e => attackRow[e] > 0 && attackRow[e] < 1); // 攻击被抗

    // 查哪些属性攻击能克制该属性（防守端）
    const weakDef = allElems.filter(atk => (chart[atk]||{})[elem] >= 2);
    const resistDef = allElems.filter(atk => (chart[atk]||{})[elem] > 0 && (chart[atk]||{})[elem] < 1);

    const strongT = strong.length ? strong.join(', ') : '无';
    const resistedT = resisted.length ? resisted.join(', ') : '无';
    const weakDefT = weakDef.length ? weakDef.join(', ') : '无';
    const resistDefT = resistDef.length ? resistDef.join(', ') : '无';

    switch (mode) {
      case 'cover':     // 打击面：克制 / 被抵抗
        return '克制: ' + strongT + '\n被抵抗: ' + resistedT;
      case 'gap':       // 打击面缺口：克制 / 被克制
        return '克制: ' + strongT + '\n被克制: ' + weakDefT;
      case 'threat':    // 高威胁属性：克制 / 抵抗
        return '克制: ' + strongT + '\n抵抗: ' + resistDefT;
      case 'noResist':  // 无抵抗属性：克制 / 被抵抗
        return '克制: ' + strongT + '\n被抵抗: ' + resistedT;
      default:
        return '克制: ' + strongT + '\n被抵抗: ' + resistedT;
    }
  },

  _toggleDropdown(e) {
    e.stopPropagation();
    const btn = e.currentTarget;
    const menu = btn.nextElementSibling;
    if (!menu || !menu.classList.contains('dropdown-menu')) return;
    document.querySelectorAll('.dropdown-menu.open').forEach(m => {
      if (m !== menu) m.classList.remove('open');
    });
    menu.classList.toggle('open');
  },

  _setDropdown(key, value) {
    this._builderFilter[key] = value;
    document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
    this._renderCurrentView();
  },

  /** 打开精灵选择器（点击空槽位） */
  _openPetSelector() {
    // 滚动到搜索框并聚焦
    const searchEl = document.getElementById('inlineSearch');
    if (searchEl) {
      searchEl.focus();
      searchEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  },

  /** 搜索输入处理（防抖+联想） */
  _onSearchInput() {
    // 更新联想词（不重渲染，安全）
    this._updateSearchSuggestions(this._searchKw);

    // 防抖重渲染
    this._searchTimer && clearTimeout(this._searchTimer);
    this._searchTimer = setTimeout(() => {
      // 重渲染前恢复搜索框焦点（用requestAnimationFrame确保DOM重建后重新聚焦）
      this._renderCurrentView();
      requestAnimationFrame(() => {
        if (this._searchInput) {
          this._searchInput.value = this._searchKw;
          this._searchInput.focus();
          // 将光标移到末尾
          const len = this._searchInput.value.length;
          this._searchInput.setSelectionRange(len, len);
        }
      });
    }, 400);
  },

  /** 搜索联想词 */
  _updateSearchSuggestions(value) {
    const { route } = Router.parse();
    if (route !== 'pets' && route !== 'skills' && route !== 'share') return;

    const old = document.getElementById('searchSuggestions');
    if (old) old.remove();

    if (!value || value.length < 1) return;

    // 获取候选列表
    let candidates = [];
    if (route === 'pets') {
      candidates = DataStore.pets.map(p => p.name).filter(n => n.includes(value));
    } else if (route === 'skills') {
      candidates = Object.keys(this._skillIndex?.byElement || {}).filter(e => e.includes(value));
      if (!candidates.length) candidates = value ? ['搜索技能...'] : [];
    } else if (route === 'share') {
      return; // 分享页不联想
    }

    candidates = candidates.slice(0, 8);
    if (!candidates.length) return;

    const rect = this._searchInput?.getBoundingClientRect();
    if (!rect) return;

    const div = document.createElement('div');
    div.id = 'searchSuggestions';
    div.style.cssText = 'position:fixed;z-index:2000;top:'+(rect.bottom+4)+'px;left:'+rect.left+'px;width:'+rect.width+'px;background:var(--white);border:1px solid var(--neutral-200);border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.12);max-height:200px;overflow-y:auto';

    for (const c of candidates) {
      const item = document.createElement('div');
      item.style.cssText = 'padding:8px 14px;font-size:13px;cursor:pointer;border-bottom:1px solid var(--neutral-100)';
      item.textContent = c;
      item.onmouseover = () => item.style.background = 'var(--neutral-50)';
      item.onmouseout = () => item.style.background = '';
      item.onclick = () => {
        this._searchKw = c;
        if (this._searchInput) this._searchInput.value = c;
        div.remove();
        this._renderCurrentView();
      };
      div.appendChild(item);
    }

    // 关闭联想（点击外部）
    document.addEventListener('click', function close(e) {
      if (!div.contains(e.target)) { div.remove(); document.removeEventListener('click', close); }
    });

    document.body.appendChild(div);
  },

  /** 右键卡片菜单 */
  _showCardMenu(event, name) {
    const menu = document.getElementById('cardCtxMenu');
    if (menu) menu.remove();
    const div = document.createElement('div');
    div.id = 'cardCtxMenu';
    div.style.cssText = 'position:fixed;z-index:3000;background:var(--white);border:1px solid var(--neutral-200);border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.12);padding:4px 0;left:'+event.clientX+'px;top:'+event.clientY+'px';
    div.innerHTML = '<div style="padding:6px 16px;cursor:pointer;font-size:13px" onmouseover="this.style.background=\'var(--neutral-50)\'" onmouseout="this.style.background=\'transparent\'" onclick="Renderer._addToTeam(\''+Utils.esc(name)+'\');document.getElementById(\'cardCtxMenu\').remove()">➕ 加入队伍</div>'
      + '<div style="padding:6px 16px;cursor:pointer;font-size:13px" onmouseover="this.style.background=\'var(--neutral-50)\'" onmouseout="this.style.background=\'transparent\'" onclick="Renderer._expandPetCard(\''+Utils.esc(name)+'\');document.getElementById(\'cardCtxMenu\').remove()">🔍 展开详情</div>';
    document.body.appendChild(div);
    document.addEventListener('click', function rm() { const m=document.getElementById('cardCtxMenu'); if(m)m.remove(); document.removeEventListener('click', rm); }, {once:true});
  },
};
