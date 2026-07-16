#!/usr/bin/env python3
"""Fix skill page: cost filter, horizontal layout, stone source column"""
with open('frontend/js/renderer.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix cost comparison: cost===c → Number(cost)===c
old = """html += '<option value="'+c+'"'+(cost===c?' selected':'')+'>'+c+'费</option>';"""
new = """html += '<option value="'+c+'"'+(Number(cost)===c?' selected':'')+'>'+c+'费</option>';"""
content = content.replace(old, new)

# 2. Merge two filter rows into one horizontal row
# Replace the builder-filter-bar section + the second filter-row with one combined row
old_filters = """    html += '<div class="builder-filter-bar"><div class="filter-row">'
      + '<button class="btn-filter'+(!elem?' active':'')+'" onclick="Renderer._skillFilterElem=\'\\';Renderer._renderCurrentView()">全部属性</button>'
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
      + '</div></div>';
    // 能耗+功能+排序
    html += '<div class="filter-row" style="margin-bottom:8px;flex-wrap:wrap">'
      + '<select class="filter-select" onchange="Renderer._skillCostFilter=this.value||null;Renderer._renderCurrentView()">'
      + '<option value="">能耗</option>';
    for (let c=0;c<=10;c++) {
      html += '<option value="'+c+'"'+(Number(cost)===c?' selected':'')+'>'+c+'费</option>';
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
      + '<option value="power_desc"'+(sortBy==='power_desc'?' selected':'')+'>威力⬇</option>'
      + '<option value="power_asc"'+(sortBy==='power_asc'?' selected':'')+'>威力⬆</option>'
      + '</select>'
      + '<span style="font-size:13px;color:var(--neutral-500);line-height:32px">'+filtered.length+'/'+allSkills.length+'</span>'
      + '</div>';"""

new_filters = """    html += '<div class="filter-row" style="margin-bottom:10px;gap:6px;flex-wrap:wrap">'
      + '<button class="btn-filter'+(!elem?' active':'')+'" onclick="Renderer._skillFilterElem=\'\\';Renderer._renderCurrentView()">全部属性</button>'
      + '<select class="filter-select" onchange="Renderer._skillFilterElem=this.value;Renderer._renderCurrentView()"><option value="">属性</option>';
    for (const e of allElements) {
      html += '<option value="'+e+'"'+(elem===e?' selected':'')+'>'+e+' ('+((this._skillIndex?.byElement[e]||[]).length)+')</option>';
    }
    html += '</select>'
      + '<select class="filter-select" onchange="Renderer._skillFilterCat=this.value;Renderer._renderCurrentView()"><option value="">分类</option>';
    for (const c of allCats) {
      html += '<option value="'+c+'"'+(cat===c?' selected':'')+'>'+c+' ('+((this._skillIndex?.byCategory[c]||[]).length)+')</option>';
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
      + '<span style="font-size:13px;color:var(--neutral-500);line-height:32px;margin-left:4px">'+filtered.length+'/'+allSkills.length+'</span>'
      + '</div>';"""

# Do replacement
count = content.count(old_filters)
print(f"Found old_filters: {count}")
if count > 0:
    content = content.replace(old_filters, new_filters)
else:
    print("old_filters not found, trying alternative approach...")
    # If the exact text didn't match, try a more flexible approach
    # Find the "全部属性" button section and replace from there
    start = content.find("+ '<button class=\"btn-filter\"+(!elem?' active':'')+'\"")
    if start > 0:
        print(f"Found alternative start at {start}")
    else:
        print("Could not find filter section")

# 3. Add skill stone source column to table header
old_header = "+ '<th>名称</th><th>属性</th><th>分类</th><th>能耗</th><th>威力</th><th>效果</th><th>使用精灵</th>'"
new_header = "+ '<th>名称</th><th>属性</th><th>分类</th><th>能耗</th><th>威力</th><th>效果</th><th>使用精灵</th><th>技能石来源</th>'"
content = content.replace(old_header, new_header)

with open('frontend/js/renderer.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
