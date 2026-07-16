#!/usr/bin/env python3
with open('frontend/js/renderer.js', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('\n  // 技能数据库\n')
end = content.find('\n  _ensureSkillIndex() {', start + 10)

with open('frontend/js/renderer_skills_new.js', 'r', encoding='utf-8') as f:
    new_func = f.read()

# Strip everything from the last appearance of _ensureSkillIndex in the new func
eol = new_func.rfind('  _ensureSkillIndex() {')
if eol > 0:
    new_func = new_func[:eol]

content = content[:start] + '\n' + new_func + content[end:]

with open('frontend/js/renderer.js', 'w', encoding='utf-8') as f:
    f.write(content)
print(f"OK: replaced {end-start} -> {len(new_func)}")
