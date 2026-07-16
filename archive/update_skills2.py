#!/usr/bin/env python3
"""Add filter/sort logic and new CSS"""
with open('frontend/js/renderer.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Add cost + func + sort filtering logic after the existing filters
old1 = """    if (cat) filtered = filtered.filter(s => (s.category||'') === cat);
    if (kw) filtered = filtered.filter(s => s.name.includes(kw) || (s.effect||'').includes(kw));
"""
new1 = """    if (cat) filtered = filtered.filter(s => (s.category||'') === cat);
    if (cost !== null && cost !== undefined && cost !== '') filtered = filtered.filter(s => s.cost === Number(cost));
    if (func) filtered = filtered.filter(s => ((s.effect||'')+(s.name||'')).includes(func));
    if (kw) filtered = filtered.filter(s => s.name.includes(kw) || (s.effect||'').includes(kw));
    if (sortBy === 'power_desc') filtered.sort((a,b) => (b.power||0)-(a.power||0));
    if (sortBy === 'power_asc') filtered.sort((a,b) => (a.power||0)-(b.power||0));
"""
content = content.replace(old1, new1)

with open('frontend/js/renderer.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ Filter logic added")
