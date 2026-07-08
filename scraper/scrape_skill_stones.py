#!/usr/bin/env python3
"""爬取技能石来源信息（从BiliWiki技能石图鉴页）"""
import json, time, requests, re
from bs4 import BeautifulSoup
from pathlib import Path

BASE = "https://wiki.biligame.com/rocom"
session = requests.Session()
session.trust_env = False
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': f'{BASE}/',
})

# 1. 获取所有技能石列表
print("▶ 获取技能石列表...")
r = session.get(f"{BASE}/%E6%8A%80%E8%83%BD%E7%9F%B3%E5%9B%BE%E9%89%B4", timeout=10)
soup = BeautifulSoup(r.text, 'lxml')
links = soup.select('a[href*="/%E6%8A%80%E8%83%BD%E7%9F%B3/"]')
skill_stones = []
seen = set()
for a in links:
    text = a.get_text(strip=True)
    href = a.get('href', '')
    if text and href and '/技能石/' in href and text not in seen:
        seen.add(text)
        skill_stones.append((text, href))
print(f"  共 {len(skill_stones)} 个技能石\n")

# 2. 逐个爬取来源信息
results = {}
for i, (name, href) in enumerate(skill_stones):
    url = f"{BASE}{href}" if href.startswith('/') else href
    try:
        r = session.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'lxml')
        # 查找来源信息
        src_div = soup.find('p', string=re.compile(r'来源'))
        if src_div:
            parent = src_div.find_next('div', class_='rocom_item_page_info_list_form')
            if parent:
                spans = parent.find_all('span')
                source = spans[-1].get_text(strip=True) if spans else ''
                if source:
                    results[name] = source
        if not name in results:
            # 备选查找
            info = soup.select_one('.rocom_item_page_info_list_form span:last-child')
            if info:
                results[name] = info.get_text(strip=True)
    except Exception as e:
        print(f"  ❌ [{i+1}] {name}: {str(e)[:40]}")

    if (i+1) % 50 == 0:
        print(f"  [{i+1}/{len(skill_stones)}] 已获取 {len(results)} 条")
    time.sleep(0.3)

# 3. 保存
output = Path("data/skill_stone_sources.json")
with open(output, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n✅ 完成: {len(results)}/{len(skill_stones)} 条")
print(f"   已保存: {output}")

# 4. 展示样例
for name in list(results.keys())[:10]:
    print(f"  {name}: {results[name][:60]}")
