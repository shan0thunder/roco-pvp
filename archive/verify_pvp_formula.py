#!/usr/bin/env python3
"""验证新的数值公式"""
import math

# PVP实例数据: (名称, 速度种族值, 性格倍率, 加点, 最终速度)
tests = [
    ("火焰猿",   60,  1.0, 0, 126),
    ("烈火守护", 65,  0.9, 0, 124),
    ("尖嘴狐仙", 100, 0.9, 0, 158),
    ("翠顶夫人", 115, 1.0, 0, 187),
    ("奇丽花",   80,  1.0, 60, 184),
    ("火神",     130, 1.1, 60, 273),
]

LV = 60

def calc_speed(race, stars, initial_iv, nature, bonus):
    """速度计算"""
    iv = initial_iv * (stars + 1)
    growth = stars * 10

    if nature > 1.0:
        nature_pct = 0.10 + stars * 0.02  # +10% + 星级×2%
    elif nature < 1.0:
        nature_pct = -0.10  # 固定-10%
    else:
        nature_pct = 0

    raw = (race + 0.5 * iv) * (0.5 + 0.01 * LV) + 10
    return math.floor(raw * (1 + nature_pct)) + growth + bonus

print("=" * 70)
print("公式验证: 速度 = [(种族+0.5×个体)×(0.5+0.01×等级)+10]×(1+性格)+成长+加点")
print("=" * 70)

# 尝试不同星级和个体值组合
for stars in range(0, 11):
    for init_iv in range(0, 36, 3):
        ok = 0
        for name, race, nature, bonus, expected in tests:
            v = calc_speed(race, stars, init_iv, nature, bonus)
            if v == expected:
                ok += 1
        if ok >= 4:
            print(f"\n星级={stars}, 初始个体={init_iv}: 匹配{ok}/6")
            for name, race, nature, bonus, expected in tests:
                v = calc_speed(race, stars, init_iv, nature, bonus)
                mark = "✅" if v == expected else "❌"
                print(f"  {mark} {name}: {v} vs {expected}")

print("\n\n最佳方案搜索...")
# 暴力搜索最优参数
best = (0, 0, 0)
best_score = 0
for stars in range(0, 11):
    for init_iv in range(1, 51):
        score = 0
        for name, race, nature, bonus, expected in tests:
            v = calc_speed(race, stars, init_iv, nature, bonus)
            if v == expected:
                score += 1
        if score > best_score:
            best_score = score
            best = (stars, init_iv, score)

print(f"最优: 星级={best[0]}, 初始个体={best[1]}, 匹配={best[2]}/6")

if best_score >= 4:
    stars, init_iv, _ = best
    print(f"\n用此参数验算:")
    for name, race, nature, bonus, expected in tests:
        v = calc_speed(race, stars, init_iv, nature, bonus)
        mark = "✅" if v == expected else "❌"
        print(f"  {mark} {name}: {v} vs {expected} 差={v-expected}")
