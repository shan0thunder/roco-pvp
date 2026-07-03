#!/usr/bin/env python3
"""
技能索引提取器
从 product_data.json 中提取所有唯一技能，建立:
  1. skills.json        — 独立技能库（含完整字段）
  2. skill_index.json   — 技能→精灵反向索引
"""
import json, sys
from pathlib import Path
from collections import defaultdict

# 加载产品数据
product_path = Path("data/product/product_data.json")
with open(product_path, "r", encoding="utf-8") as f:
    data = json.load(f)

pets = data.get("pets", [])
print(f"精灵总数: {len(pets)}")

# 提取所有技能
skill_map = {}       # name → skill_detail
skill_to_pets = defaultdict(list)  # skill_name → [pet_names]

for pet in pets:
    pname = pet.get("name", "")
    for skill in pet.get("skills", []):
        sname = skill.get("name", "")
        if not sname:
            continue

        # 去重合并（保持第一次出现的完整信息）
        if sname not in skill_map:
            skill_map[sname] = {
                "name": sname,
                "element": skill.get("element") or "",
                "category": skill.get("category") or "",
                "cost": skill.get("cost"),
                "power": skill.get("power"),
                "effect": skill.get("effect", ""),
                "source": skill.get("source", ""),
                "source_type": skill.get("source_type", "默认"),
            }

        # 记录谁有这个技能
        skill_to_pets[sname].append(pname)

print(f"独立技能数: {len(skill_map)}")

# 构建索引: 按属性/分类分组
by_element = defaultdict(list)
by_category = defaultdict(list)
for sname, skill in skill_map.items():
    elem = skill.get("element") or "无"
    cat = skill.get("category") or "无"
    by_element[elem].append(sname)
    by_category[cat].append(sname)

# 保存技能库
skills_list = list(skill_map.values())
skills_path = Path("data/skills.json")
with open(skills_path, "w", encoding="utf-8") as f:
    json.dump(skills_list, f, ensure_ascii=False, indent=2)
print(f"技能库已保存: {skills_path} ({len(skills_list)} 个)")

# 保存索引
index_data = {
    "total_skills": len(skill_map),
    "total_pets_with_skills": len([p for p in pets if p.get("skills")]),
    "skill_to_pets": dict(skill_to_pets),
    "by_element": dict(by_element),
    "by_category": dict(by_category),
    "element_counts": {e: len(v) for e, v in sorted(by_element.items(), key=lambda x: -len(x[1]))},
    "category_counts": {c: len(v) for c, v in sorted(by_category.items(), key=lambda x: -len(x[1]))},
}

# 技能→精灵映射: 按技能名排序，限制精灵列表长度（前端显示用）
index_data["skill_to_pets_short"] = {
    s: (pets_list[:50], len(pets_list))
    for s, pets_list in skill_to_pets.items()
}

index_path = Path("data/skill_index.json")
with open(index_path, "w", encoding="utf-8") as f:
    json.dump(index_data, f, ensure_ascii=False, indent=2)
print(f"技能索引已保存: {index_path}")

# 统计输出
print(f"\n技能属性分布:")
for elem, count in sorted(by_element.items(), key=lambda x: -len(x[1])):
    print(f"  {elem}: {count}")

print(f"\n技能分类分布:")
for cat, count in sorted(by_category.items(), key=lambda x: -len(x[1])):
    print(f"  {cat}: {count}")

# 更新产品数据的索引
print(f"\n更新 product_data.json 中的技能索引...")
data["index"]["skills_by_element"] = dict(by_element)
data["index"]["skills_by_category"] = dict(by_category)
data["index"]["skill_to_pets"] = dict(skill_to_pets)
data["_meta"]["total_records"]["skills_total_unique"] = len(skill_map)

with open(product_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("product_data.json 技能索引已更新")
print(f"\n✅ 完成!")
