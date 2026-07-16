#!/usr/bin/env python3
"""Minimal targeted fixes for renderer.js"""
import re

with open('frontend/js/renderer.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix cost===c → Number(cost)===c
content = content.replace("+(cost===c?' selected':'')+'>'+c+'费'", "+(Number(cost)===c?' selected':'')+'>'+c+'费'")

# 2. Add stone source column to table header
content = content.replace(
    "<th>使用精灵</th>",
    "<th>使用精灵</th><th>来源</th>"
)

# 3. Load stone data after skill index init
content = content.replace(
    "await this._ensureSkillIndex();\n    const allSkills",
    "await this._ensureSkillIndex();\n    if (!this._stoneMap) {\n      try { const r = await fetch('data/skill_stone_sources.json'); if (r.ok) this._stoneMap = await r.json(); } catch(e) {}\n    }\n    const allSkills"
)

# 4. Add stoneMap variable
content = content.replace(
    "const skillToPets = this._skillIndex?.skillToPets || {};\n    const elem",
    "const skillToPets = this._skillIndex?.skillToPets || {};\n    const stoneMap = this._stoneMap || {};\n    const elem"
)

# 5. Add stone cell and fix colspan
# Find pattern: end of td + </tr> + expanded row with colspan=7
old_td = "color:var(--primary-500)\">'+more+'</span></td>'\n        + '</tr>'\n        + (isExpanded ? '<tr class=\"skill-pets-row\"><td colspan=\"7\">"
new_td = "color:var(--primary-500)\">'+more+'</span></td>'\n        + '<td style=\"font-size:11px;color:var(--neutral-400);max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap\" title=\"'+Utils.esc(stoneMap[s.name]||'')+'\" rel=\"nofollow\">'+Utils.esc(stoneMap[s.name]||'—')+'</td>'\n        + '</tr>'\n        + (isExpanded ? '<tr class=\"skill-pets-row\"><td colspan=\"8\">'"
content = content.replace(old_td, new_td)

with open('frontend/js/renderer.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
