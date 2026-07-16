#!/usr/bin/env python3
"""Clean fix: merge filter rows, fix cost, add stone source"""
with open('frontend/js/renderer.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix cost===c -> Number(cost)===c
content = content.replace("+(cost===c?' selected':'')+'>'+c+'费'", "+(Number(cost)===c?' selected':'')+'>'+c+'费'")

# 2. Merge filters - replace the two separate filter rows with one combined row
# Find the "全部属性" button section and everything until the search bar section
old_marker = "// 筛选栏"
new_marker = "// 使用顶栏搜索框"
start = content.find(old_marker, 690)
end = content.find(new_marker, start)

if start > 0 and end > start:
    # Build new combined filter section
    indent = '    '
    new_filters = f'''{indent}// 筛选栏（横向排列）
{indent}html += '<div class="filter-row" style="margin-bottom:10px;gap:6px;flex-wrap:wrap">'
{indent}  + '<button class="btn-filter'+(!elem?' active':'')+'" onclick="Renderer._skillFilterElem=\\'\\';Renderer._renderCurrentView()">全部</button>'
{indent}  + '<select class="filter-select" onchange="Renderer._skillFilterElem=this.value;Renderer._renderCurrentView()"><option value="">属性</option>';
{indent}for (const e of allElements) {{
{indent}  html += '<option value="'+e+'"'+(elem===e?' selected':'')+'>'+e+'</option>';
{indent}}}
{indent}  html += '</select>'
{indent}  + '<select class="filter-select" onchange="Renderer._skillFilterCat=this.value;Renderer._renderCurrentView()"><option value="">分类</option>';
{indent}for (const c of allCats) {{
{indent}  html += '<option value="'+c+'"'+(cat===c?' selected':'')+'>'+c+'</option>';
{indent}}}
{indent}  html += '</select>'
{indent}  + '<select class="filter-select" onchange="Renderer._skillCostFilter=this.value;Renderer._renderCurrentView()"><option value="">能耗</option>';
{indent}for (let c=0;c<=10;c++) {{
{indent}  html += '<option value="'+c+'"'+(Number(cost)===c?' selected':'')+'>'+c+'费</option>';
{indent}}}
{indent}  html += '</select>'
{indent}  + '<select class="filter-select" onchange="Renderer._skillFuncFilter=this.value;Renderer._renderCurrentView()"><option value="">功能</option>'
{indent}  + '<option value="清强化"'+(func==='清强化'?' selected':'')+'>清强化</option>'
{indent}  + '<option value="印记"'+(func==='印记'?' selected':'')+'>印记</option>'
{indent}  + '<option value="清印记"'+(func==='清印记'?' selected':'')+'>清印记</option>'
{indent}  + '<option value="回血"'+(func==='回血'?' selected':'')+'>回血</option>'
{indent}  + '<option value="护盾"'+(func==='护盾'?' selected':'')+'>护盾</option>'
{indent}  + '<option value="先手"'+(func==='先手'?' selected':'')+'>先手</option>'
{indent}  + '</select>'
{indent}  + '<select class="filter-select" onchange="Renderer._skillSortBy=this.value;Renderer._renderCurrentView()"><option value="">排序</option>'
{indent}  + '<option value="power_desc"'+(sortBy==='power_desc'?' selected':'')+'>威力⬇</option>'
{indent}  + '<option value="power_asc"'+(sortBy==='power_asc'?' selected':'')+'>威力⬆</option>'
{indent}  + '</select>'
{indent}  + '<span style="font-size:13px;color:var(--neutral-400);line-height:32px;margin-left:4px">'+filtered.length+'/'+allSkills.length+'</span>'
{indent}  + '</div>';
'''
    content = content[:start] + '\n' + new_filters + content[end:]
    print(f"Replaced filter section ({end-start} -> {len(new_filters)})")
else:
    print(f"Markers not found: start={start}, end={end}")

# 3. Add stone source column header
content = content.replace(
    "<th>使用精灵</th><th>来源</th>",
    "<th>使用精灵</th><th>来源</th>"
)

# 4. Load stone sources and add to table
# Add stone source loading before the rendering
stone_marker = "const skillToPets = this._skillIndex?.skillToPets || {};"
if stone_marker in content:
    stone_load = "const stoneMap = {}; try { const r = await fetch('data/skill_stone_sources.json'); if(r.ok) { const d = await r.json(); Object.assign(stoneMap, d); } } catch(e){}"
    content = content.replace(stone_marker, stone_marker + '\n    ' + stone_load)
    print("Added stone source loading")

# 5. Add stone cell in table rows
old_cell = "+ '<td style=\"font-size:12px;color:var(--neutral-500)\">'+petNames+'<span style=\"color:var(--primary-500)\">'+more+'</span></td>'"
new_cell = "+ '<td style=\"font-size:12px;color:var(--neutral-500)\">'+petNames+'<span style=\"color:var(--primary-500)\">'+more+'</span></td>'\\n"
new_cell += "        + '<td style=\"font-size:11px;color:var(--neutral-400);max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap\" title=\"'+Utils.esc(stoneMap[s.name]||'')+'\" rel=\"nofollow\">'+Utils.esc(stoneMap[s.name]||'—')+'</td>'"
content = content.replace(old_cell, new_cell)

with open('frontend/js/renderer.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
