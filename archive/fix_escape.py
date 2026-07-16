#!/usr/bin/env python3
"""Fix escape issues in renderer.js"""
import re

with open('frontend/js/renderer.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: onclick="Renderer._skillFilterElem='';Renderer._renderCurrentView()"
# The Python-generated code has broken quotes like onclick=""Renderer...
# Fix specific patterns
fixes = [
    ('onclick="Renderer._skillFilterElem=\\\'\\\';Renderer._renderCurrentView()"', "onclick=\"Renderer._skillFilterElem='';Renderer._renderCurrentView()\""),
    ('onclick="Renderer._skillFilterCat=this.value;Renderer._renderCurrentView()"', "onclick=\"Renderer._skillFilterCat=this.value;Renderer._renderCurrentView()\""),
    ('onclick="Renderer._skillCostFilter=this.value?Number(this.value):null;Renderer._renderCurrentView()"', "onclick=\"Renderer._skillCostFilter=this.value?Number(this.value):null;Renderer._renderCurrentView()\""),
    ('onclick="Renderer._skillFuncFilter=this.value;Renderer._renderCurrentView()"', "onclick=\"Renderer._skillFuncFilter=this.value;Renderer._renderCurrentView()\""),
    ('onclick="Renderer._skillSortBy=this.value;Renderer._renderCurrentView()"', "onclick=\"Renderer._skillSortBy=this.value;Renderer._renderCurrentView()\""),
    ('onclick="Renderer._toggleSkillExpand(\\\'', "onclick=\"Renderer._toggleSkillExpand('"),
    ("onclick=\"Renderer._toggleSkillExpand('", "onclick=\"Renderer._toggleSkillExpand('"),
    ("Renderer._renderCurrentView()\\\")", "Renderer._renderCurrentView()\")"),
    ("Renderer._renderCurrentView()')", "Renderer._renderCurrentView()')\""),
    ("Router.go(\\'pet\\',\\'", "Router.go('pet','"),
    ("Router.go('pet','", "Router.go('pet','"),
    ("'\\');Renderer._renderCurrentView()\">", "');Renderer._renderCurrentView()\">"),
]

for old, new in fixes:
    content = content.replace(old, new)

with open('frontend/js/renderer.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed")
