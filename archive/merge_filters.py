#!/usr/bin/env python3
with open('frontend/js/renderer.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace everything from "// 筛选栏" to the end of the second filter row
# The second filter row ends with "'</div>';" after the count span
old_start = "    // 筛选栏"
# Find the exact end - look for the pattern after the last filter-row closing
pos_start = content.find(old_start, 690)
pos_end_search = content.find("'</div>';", pos_start + 100)
# Find the NEXT </div>'; after that (there are two closings)
pos_end = content.find("'</div>';", pos_end_search + 10)
if pos_end > pos_start:
    pos_end += len("'</div>';")
else:
    pos_end = pos_end_search + len("'</div>';")

new_section = """    // 筛选栏（横向排列）
    html += '<div class="filter-row" style="margin-bottom:10px;gap:6px;flex-wrap:wrap">'
      + '<select class="filter-select" onchange="Renderer._skillFilterElem=this.value;Renderer._renderCurrentView()"><option value="">全部属性</option>';
    for (const e of allElements) {
      html += '<option value="'+e+'"'+(elem===e?' selected':'')+'>'+e+' ('+((byElem[e]||[]).length)+')</option>';
    }
    html += '</select>'
      + '<select class="filter-select" onchange="Renderer._skillFilterCat=this.value;Renderer._renderCurrentView()"><option value="">分类</option>';
    for (const c of allCats) {
      html += '<option value="'+c+'"'+(cat===c?' selected':'')+'>'+c+' ('+((byCat[c]||[]).length)+')</option>';
    }
    html += '</select>'
      + '<select class="filter-select" onchange="Renderer._skillCostFilter=this.value||null;Renderer._renderCurrentView()"><option value="">能耗</option>';
    for (let c=0;c<=10;c++) {
      html += '<option value="'+c+'"'+(Number(cost)===c?' selected':'')+'>'+c+'费</option>';
    }
    html += '</select>'
      + '<select class="filter-select" onchange="Renderer._skillFuncFilter=this.value;Renderer._renderCurrentView()"><option value="">功能</option>'
      + '<option value="清强化"'+(func==='清强化'?' selected':'')+'>清强化</option>'
      + '<option value="印记"'+(func==='印记'?' selected':'')+'>印记</option>'
      + '<option value="清印记"'+(func==='清印记'?' selected':'')+'>清印记</option>'
      + '<option value="回血"'+(func==='回血'?' selected':'')+'>回血</option>'
      + '<option value="护盾"'+(func==='护盾'?' selected':'')+'>护盾</option>'
      + '<option value="先手"'+(func==='先手'?' selected':'')+'>先手</option>'
      + '</select>'
      + '<select class="filter-select" onchange="Renderer._skillSortBy=this.value;Renderer._renderCurrentView()"><option value="">排序</option>'
      + '<option value="power_desc"'+(sortBy==='power_desc'?' selected':'')+'>威力⬇</option>'
      + '<option value="power_asc"'+(sortBy==='power_asc'?' selected':'')+'>威力⬆</option>'
      + '</select>'
      + '<span style="font-size:13px;color:var(--neutral-400);line-height:32px;margin-left:4px">'+filtered.length+'/'+allSkills.length+'</span>'
      + '</div>';
"""

content = content[:pos_start] + new_section + content[pos_end:]

with open('frontend/js/renderer.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
