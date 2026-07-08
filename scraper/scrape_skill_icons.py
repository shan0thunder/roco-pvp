#!/usr/bin/env python3
"""爬取所有技能图标"""
import json, time, requests
from bs4 import BeautifulSoup

BASE = "https://wiki.biligame.com/rocom"
session = requests.Session()
session.trust_env = False
session.headers.update({'User-Agent':'Mozilla/5.0','Referer':f'{BASE}/'})

# 加载已有数据
with open("data/product/product_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 获取所有精灵名（优先爬技能数多的）
pets_sorted = sorted(data["pets"], key=lambda p: -(p.get("skills_count",0) or 0))
print(f"精灵总数: {len(pets_sorted)}")

# 已获取的图标映射
icon_map = {}
existing = set()

for i, pet in enumerate(pets_sorted):
    name = pet["name"]
    src = pet.get("source_url", "")
    if not src:
        continue

    # 跳过已有图标的技能（加速）
    pet_skills = [s["name"] for s in (pet.get("skills") or [])]
    if all(s in icon_map for s in pet_skills):
        continue

    try:
        r = session.get(src, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        for card in soup.select(".skill-single"):
            sname_el = card.select_one(".skill-name")
            if not sname_el:
                continue
            sname = sname_el.get_text(strip=True)
            if not sname or sname in icon_map:
                continue
            img_el = card.select_one(".skill-single-head img")
            if img_el and img_el.get("src"):
                # 取原图 URL (去掉 thumb 路径)
                src_url = img_el["src"]
                if "/thumb/" in src_url:
                    src_url = src_url.replace("/thumb/", "/")
                    last_slash = src_url.rfind("/")
                    if last_slash > 0:
                        src_url = src_url[:last_slash]
                icon_map[sname] = src_url
    except:
        pass

    if (i+1) % 50 == 0:
        print(f"  [{i+1}/{len(pets_sorted)}] 已获取 {len(icon_map)} 个图标")
    time.sleep(0.3)

# 保存
output = {"_note": "技能图标URL映射", "icons": icon_map}
with open("data/skill_icons.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n完成: {len(icon_map)} 个技能图标")
missing = [s["name"] for p in data["pets"] for s in (p.get("skills") or []) if s["name"] not in icon_map]
print(f"缺失: {len(set(missing))} 个")
