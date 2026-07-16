#!/usr/bin/env python3
"""
迪莫 — 速度值计算(已验证公式)
"""
import math

LV = 60
IV = 31  # 满个体

print("="*70)
print("迪莫 速度值精确计算")
print("种族值: 92 | 性格: 天真(+速度×1.1, -魔防×0.9)")
print("加点: 物攻+6, 魔攻+6 (不影响速度)")
print("公式: floor(((2×B + 31 + EV/4) × 0.6 + 5) × Nature) + 分配")
print("="*70)

BASE_SPEED = 92
NATURE = 1.1

print(f"\n速度种族值: {BASE_SPEED}")
print(f"\n不同努力值(EV)投入的结果:")

for ev in [0, 36, 76, 116, 156, 196, 236, 252]:
    raw = ((2*BASE_SPEED + IV + ev//4) * LV / 100) + 5
    v = math.floor(raw * NATURE)
    print(f"  EV={ev:3d} (速): {v}")

# 用户加点各6- 如果指潜能分配(非EV)
print(f"\n如果'加6-'是潜能分配(直接+6速, 类似火神的+60):")
print(f"  EV=0: {math.floor((((2*BASE_SPEED + 31 + 0) * 0.6 + 5) * 1.1)) + 6}")

# 加上用户的迪莫全属性计算
print("\n" + "="*70)
print("迪莫 60级满星 全属性(假设加点6为潜能)")
print("加点: 物攻+6潜能, 魔攻+6潜能, 速度+0潜能")
print("性格: 天真 (+速度,-魔防)")
print("="*70)

# 迪莫全种族值
stats = {
    'hp': 120,
    'attack': 80,        # 物攻
    'defense': 105,      # 物防
    'magic_attack': 80,  # 魔攻
    'magic_defense': 105,# 魔防
    'speed': 92,         # 速度
}

# 假设努力值分配(252大法-极限单项)
# scenario A: 极速252, 其余自由
# scenario B: 均衡分配
# scenario C: 攻速252

# 给几种方案
scenarios = [
    ("A-极速",        {'speed': 252}),
    ("B-攻速",        {'attack': 252, 'speed': 252, 'magic_attack': 6}),
    ("C-均衡",        {'hp': 84, 'attack': 84, 'defense': 84, 'speed': 84}),
    ("D-物攻极速",    {'attack': 252, 'speed': 252}),
]

# 加点(潜能)分配: 物攻+6, 魔攻+6
bonus = {'attack': 6, 'magic_attack': 6}
nature = {
    'hp': 1.0,
    'attack': 1.0,
    'defense': 1.0,
    'magic_attack': 1.0,
    'magic_defense': 0.9,
    'speed': 1.1,
}

for sname, evs in scenarios:
    print(f"\n--- 方案{sname} ---")
    total = 0
    for stat, base in stats.items():
        ev = evs.get(stat, 0)
        bns = bonus.get(stat, 0)
        n = nature[stat]

        if stat == 'hp':
            raw = ((2*base + IV + ev//4) * LV / 100) + LV + 10
        else:
            raw = ((2*base + IV + ev//4) * LV / 100) + 5

        final = math.floor(raw * n) + bns
        total += final
        print(f"  {stat:15s}: base={base:3d} EV={ev:3d} 潜能={bns:1d} ×性格{n:.1f} → {final}")
    print(f"  {'种族值总和':15s}: {582}")
    print(f"  {'能力值总和':15s}: {total}")
