  /** 技能数据库 */
  async _renderSkills() {
    const data = await DataStore.load();
    await this._ensureSkillIndex();
    const allSkills = this._skillIndex?.allSkills || [];
    const skillToPets = this._skillIndex?.skillToPets || {};
    const elem = this._skillFilterElem || '';
    const cat = this._skillFilterCat || '';
    const cost = this._skillCostFilter;
    const func = this._skillFuncFilter || '';
    const sortBy = this._skillSortBy || '';
    const kw = this._searchKw?.toLowerCase() || '';
    const expanded = this._skillExpanded;

    let filtered = allSkills;
    if (elem) filtered = filtered.filter(s => (s.element||'') === elem);
    if (cat) filtered = filtered.filter(s => (s.category||'') === cat);
    if (cost!=null && cost!==undefined && cost!=='') filtered = filtered.filter(s => s.cost === Number(cost));
    if (func) filtered = filtered.filter(s => ((s.effect||'')+(s.name||'')).includes(func));
    if (kw) filtered = filtered.filter(s => s.name.includes(kw) || (s.effect||'').includes(kw));
    if (sortBy === 'power_desc') filtered.sort((a,b) => (b.power||0)-(a.power||0));
    if (sortBy === 'power_asc') filtered.sort((a,b) => (a.power||0)-(b.power||0));
    if (sortBy === 'cost_asc') filtered.sort((a,b) => (a.cost||0)-(b.cost||0));
    if (sortBy === 'cost_desc') filtered.sort((a,b) => (b.cost||0)-(a.cost||0));

    const allElements = [...new Set(allSkills.map(s => s.element).filter(Boolean))].sort();
    const allCats = [...new Set(allSkills.map(s => s.category).filter(Boolean))].sort();

    let html = '<div class="page-header"><h2>技能数据库</h2><p>点击展开查看会此技能的精灵</p></div>';

    // 筛选栏
    html += '<div class="builder-filter-bar"><div class="filter-row" style="flex-wrap:wrap">'
      + '<button class="btn-filter'+(!elem?' active':'')+'" onclick="Renderer._skillFilterElem=\'\';Renderer._renderCurrentView()">全部属性</button>'
      + '<select class="filter-select" onchange="Renderer._skillFilterElem=this.value;Renderer._renderCurrentView()">'
      + '<option value="">属性</option>';
    for (const e of allElements) {
      html += '<option value="'+e+'"'+(elem===e?' selected':'')+'>'+e+' ('+((this._skillIndex?.byElement[e]||[]).length)+')</option>';
    }
    html += '</select>'
      + '<select class="filter-select" onchange="Renderer._skillFilterCat=this.value;Renderer._renderCurrentView()">'
      + '<option value="">分类</option>';
    for (const c of allCats) {
      html += '<option value="'+c+'"'+(cat===c?' selected':'')+'>'+c+' ('+((this._skillIndex?.byCategory[c]||[]).length)+')</option>';
    }
    html += '</select>'
      + '<select class="filter-select" onchange="Renderer._skillCostFilter=this.value?Number(this.value):null;Renderer._renderCurrentView()">'
      + '<option value="">能耗</option>';
    for (let c=0;c<=10;c++) {
      html += '<option value="'+c+'"'+(cost===c?' selected':'')+'>'+c+'费</option>';
    }
    html += '</select>'
      + '<select class="filter-select" onchange="Renderer._skillFuncFilter=this.value;Renderer._renderCurrentView()">'
      + '<option value="">功能</option>'
      + '<option value="清强化"'+(func==='清强化'?' selected':'')+'>清强化</option>'
      + '<option value="印记"'+(func==='印记'?' selected':'')+'>印记</option>'
      + '<option value="清印记"'+(func==='清印记'?' selected':'')+'>清印记</option>'
      + '<option value="回血"'+(func==='回血'?' selected':'')+'>回血</option>'
      + '<option value="护盾"'+(func==='护盾'?' selected':'')+'>护盾</option>'
      + '<option value="先手"'+(func==='先手'?' selected':'')+'>先手</option>'
      + '</select>'
      + '<select class="filter-select" onchange="Renderer._skillSortBy=this.value;Renderer._renderCurrentView()">'
      + '<option value="">排序</option>'
      + '<option value="power_desc"'+(sortBy==='power_desc'?' selected':'')+'>威力由高到低</option>'
      + '<option value="power_asc"'+(sortBy==='power_asc'?' selected':'')+'>威力由低到高</option>'
      + '<option value="cost_asc"'+(sortBy==='cost_asc'?' selected':'')+'>能耗由低到高</option>'
      + '<option value="cost_desc"'+(sortBy==='cost_desc'?' selected':'')+'>能耗由高到低</option>'
      + '</select>'
      + '<span style="font-size:13px;color:var(--neutral-500);line-height:32px">'+filtered.length+'/'+allSkills.length+'</span>'
      + '</div></div>';

    this._showSearch(true);
    if (this._searchInput) {
      this._searchInput.value = this._searchKw || '';
      this._searchInput.setAttribute('placeholder', '搜索技能名或效果...');
    }

    // 技能列表卡片
    html += '<div class="skill-list">';
    for (const s of filtered) {
      const petsWith = skillToPets[s.name] || [];
      const isExpanded = expanded === s.name;

      html += '<div class="skill-item'+(isExpanded?' expanded':'')+'" onclick="Renderer._toggleSkillExpand(\''+Utils.esc(s.name)+'\')">'
        + '<div class="skill-item-main">'
        + '<div class="skill-item-hdr">'
        + '<span class="skill-item-name">'+Utils.esc(s.name)+'</span>'
        + '<span class="card-tag" style="background:'+Utils.elementColor(s.element)+';color:#fff">'+Utils.esc(s.element||'-')+'</span>'
        + '<span class="skill-item-tag">'+Utils.esc(s.category||'-')+'</span>'
        + '<span class="skill-item-tag">'+(s.cost!=null?s.cost+'费':'—')+'</span>'
        + '<span class="skill-item-tag">'+(s.power!=null?s.power+'威':'—')+'</span>'
        + '</div>'
        + '<div class="skill-item-eff">'+Utils.esc((s.effect||'').slice(0,80))+'</div>'
        + '<span class="skill-item-arrow">'+(isExpanded?'▲':'▼')+'</span>'
        + '</div>';
      if (isExpanded) {
        html += '<div class="skill-item-pets">';
        if (petsWith.length) {
          for (const pn of petsWith) {
            html += '<span class="skill-pet-link" onclick="event.stopPropagation();Router.go(\'pet\',\''+Utils.esc(pn)+'\');Renderer._renderCurrentView()">'+Utils.esc(pn)+'</span>';
          }
        } else {
          html += '<span style="font-size:12px;color:var(--neutral-500)">暂无</span>';
        }
        html += '</div>';
      }
      html += '</div>';
    }
    html += '</div>';
    if (!filtered.length) html += '<div class="empty-state">未找到匹配的技能</div>';
    this._container.innerHTML = html;
  },

  _toggleSkillExpand(name) {
    this._skillExpanded = this._skillExpanded === name ? null : name;
    this._renderCurrentView();
  },

  _ensureSkillIndex() {
    // remaining implementation unchanged