#!/usr/bin/env python3
"""Rewrite _renderSkills with new features"""
with open('frontend/js/renderer.js', 'r', encoding='utf-8') as f:
    content = f.read()

# First, check what the file looks like around _renderSkills
import re

# Find the exact function boundaries
start_idx = content.find('async _renderSkills()')
end_idx = content.find('_ensureSkillIndex()', start_idx + 100)

print(f'renderSkills at {start_idx}, ensureSkillIndex at {end_idx}')

# Find the table rendering section (old way) and replace it
old_table = """    // 技能表格
    html += '<div style="overflow-x:auto"><table class="skill-table" style="font-size:13px"><thead><tr>'
      + '<th>名称</th><th>属性</th><th>分类</th><th>能耗</th><th>威力</th><th>效果</th><th>使用精灵</th>'
      + '</tr></thead><tbody>';

    for (const s of filtered) {
      const petsWith = skillToPets[s.name] || [];
      const petNames = petsWith.slice(0, 4).map(n => Utils.esc(n)).join(', ');
      const more = petsWith.length > 4 ? '...等'+petsWith.length+'只' : '';

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

  _ensureSkillIndex() {"""

new_cards = """    html += '<div class="skill-list">';
    for (const s of filtered) {
      const petsWith = skillToPets[s.name] || [];
      const isExpanded = expanded === s.name;

      html += '<div class="skill-item'+(isExpanded?' expanded':'')+'" onclick="Renderer._toggleSkillExpand(\\''+Utils.esc(s.name)+'\\')">'
        + '<div class="skill-item-main">'
        + '<div class="skill-item-hdr">'
        + '<span class="skill-item-name">'+Utils.esc(s.name)+'</span>'
        + '<span class="card-tag" style="background:'+Utils.elementColor(s.element)+';color:#fff;font-size:10px">'+Utils.esc(s.element||'-')+'</span>'
        + '<span class="skill-badge">'+Utils.esc(s.category||'-')+'</span>'
        + '<span class="skill-badge">'+(s.cost!=null?s.cost+'费':'—')+'</span>'
        + '<span class="skill-badge">'+(s.power!=null?s.power+'威力':'—')+'</span>'
        + '</div>'
        + '<div class="skill-item-eff">'+Utils.esc((s.effect||'').slice(0,80))+'</div>'
        + '</div>';
      if (isExpanded) {
        html += '<div class="skill-item-pets">';
        for (const pn of petsWith) {
          html += '<span class="skill-pet" onclick="event.stopPropagation();Router.go(\\'pet\\',\\''+Utils.esc(pn)+'\\');Renderer._renderCurrentView()">'+Utils.esc(pn)+'</span>';
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

  _ensureSkillIndex() {"""

content = content.replace(old_table, new_cards)

with open('frontend/js/renderer.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
