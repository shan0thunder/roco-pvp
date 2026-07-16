import re

with open('frontend/js/renderer.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: onclick="Renderer._skillFilterElem='';Renderer..."
# Change to use single quotes for onclick
old = "onclick=\"Renderer._skillFilterElem='';Renderer._renderCurrentView()\""
new = "onclick='Renderer._skillFilterElem=\"\";Renderer._renderCurrentView()'"
content = content.replace(old, new)

# Fix 2: onclick="Renderer._toggleSkillExpand('name')"
# The issue is quotes inside quotes. Use single quotes for onclick.
old2 = "onclick=\"Renderer._toggleSkillExpand('"
new2 = "onclick='Renderer._toggleSkillExpand("
content = content.replace(old2, new2)

# Fix 3: Fix the closing of toggle expand onclick
old3 = "');Renderer._renderCurrentView()\">"
new3 = ");Renderer._renderCurrentView()\">"
content = content.replace(old3, new3)

with open('frontend/js/renderer.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed")
