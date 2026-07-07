#!/usr/bin/env python3
"""从 BiliWiki 提取精灵特性（被动能力）"""
import json, time, re, sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://wiki.biligame.com/",
}

# 加载当前产品数据
with open("data/product/product_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

pets = data["pets"]
print(f"精灵总数: {len(pets)}")

# 已经有特性的精灵数
has_trait = sum(1 for p in pets if p.get("trait"))
print(f"已有特性: {has_trait}")

BASE = "https://wiki.biligame.com/rocom"
extracted = 0

for i, pet in enumerate(pets):
    if pet.get("trait"):
        continue  # 跳过已有特性的

    name = pet["name"]
    source_url = pet.get("source_url", "")
    if not source_url:
        continue

    try:
        resp = requests.get(source_url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            continue
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        trait_el = soup.select_one(".sprite-trait-body")
        if trait_el:
            name_el = trait_el.select_one(".sprite-trait-name")
            desc_el = trait_el.select_one(".sprite-trait-desc")
            tname = name_el.get_text(strip=True) if name_el else ""
            tdesc = desc_el.get_text(strip=True) if desc_el else ""
            if tname or tdesc:
                pet["trait"] = {"name": tname, "desc": tdesc}
                extracted += 1
                if extracted <= 3 or extracted % 50 == 0:
                    print(f"  [{i+1}/{len(pets)}] {name}: {tname} - {tdesc[:40]}")

    except Exception as e:
        print(f"  [{i+1}] {name}: 失败 - {str(e)[:40]}")

    time.sleep(0.3)

# 保存
with open("data/product/product_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 提取完成: 新增 {extracted} 条特性")
print(f"   总计: {sum(1 for p in pets if p.get('trait'))}/{len(pets)} 只精灵有特性")
