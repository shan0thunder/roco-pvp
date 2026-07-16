#!/usr/bin/env python3
"""
最终校准 — 用迪莫PVP数据验证公式
迪莫: 性格+速度, +60速, 速度=223
"""
import math

LV = 60

# ===== 用迪莫PVP数据校准公式 =====
# 迪莫 speed: base=92, nature=1.1, +60分配, 结果=223
# 公式值 = 223 - 60 = 163
# floor(((184 + IV + EV/4) * 0.6 + 5) * 1.1) = 163

# 找IV和EV的最佳组合
print("="*70)
print("公式校准 — 迪莫(性格+速度, +60) → 223")
print("="*70)
print("\n满个体(IV=31)时, 需要努力值EV多少?\n")

for ev in range(0, 256, 4):
    raw = ((2*92 + 31 + ev//4) * LV / 100) + 5
    v = math.floor(raw * 1.1)
    if v + 60 == 223:
        print(f"  ✅ IV=31, EV={ev:3d}: 公式值={v}, +60={v+60} = 223 ✓")
    elif v + 60 in [222, 224]:
        print(f"  ⚠ IV=31, EV={ev:3d}: 公式值={v}, +60={v+60} (接近223)")

print("\n" + "="*70)
print("概念解释")
print("="*70)
print("""
1. 满个体(个体值/天赋 IV=31)
   - 每只精灵出生时随机 0-31 的天赋值
   - 31是最大值, 称为"满个体"
   - 影响最终能力值, 每1点IV → 约0.6能力值(60级)
   - 类似宝可梦的"个体值"

2. 努力值(努力值 EV)
   - 通过战斗或道具提升, 最高252/项
   - 宝可梦机制: 每4点EV → 1能力值(100级时)
   - 60级时效: 每4.4点EV ≈ 1能力值
   - 你的例子中精灵速度EV大多在96~244之间

3. 潜能分配(加点)
   - 即你写的"+60"或"+6"
   - 直接加到最终能力值上, 不经过公式
   - 你的"加6-" = 分配6点潜能到该属性
""")

# ===== 迪莫完整计算 =====
print("="*70)
print("迪莫 60级 满个体 完整数值")
print("加点: 物攻+6潜能, 魔攻+6潜能 (速度不加)")
print("性格: 天真 (+速度×1.1, -魔防×0.9)")
print("="*70)

# 迪莫种族值
STATS = {
    '生命':   ('hp', 120),
    '物攻':   ('attack', 80),
    '物防':   ('defense', 105),
    '魔攻':   ('magic_attack', 80),
    '魔防':   ('magic_defense', 105),
    '速度':   ('speed', 92),
}

# 性格修正
NATURE = {
    'hp': 1.0,
    'attack': 1.0,
    'defense': 1.0,
    'magic_attack': 1.0,
    'magic_defense': 0.9,
    'speed': 1.1,
}

# 潜能分配
BONUS = {'attack': 6, 'magic_attack': 6}

# 几种努力值分配方案
scenarios = [
    ("不加速度",     {'hp': 252, 'attack': 252, 'magic_attack': 6}),
    ("极速(252速)",  {'hp': 252, 'speed': 252, 'attack': 6}),
    ("攻速252",      {'attack': 252, 'speed': 252}),
    ("均衡各84",     {'hp': 84, 'attack': 84, 'defense': 84, 'speed': 84}),
    ("仅加双攻",     {'attack': 252, 'magic_attack': 252, 'speed': 6}),
]

for sname, evs in scenarios:
    print(f"\n--- {sname} ---")
    for label, (key, base) in STATS.items():
        ev = evs.get(key, 0)
        bns = BONUS.get(key, 0)
        n = NATURE[key]

        if key == 'hp':
            raw = ((2*base + 31 + ev//4) * LV / 100) + LV + 10
        else:
            raw = ((2*base + 31 + ev//4) * LV / 100) + 5

        final = math.floor(raw * n) + bns
        print(f"  {label:6s}: base={base:3d} EV={ev:3d} 潜能+{bns} ×性格{n} → {final:3d}")

    # 如果是极速方案, 验证+60速的情况
    if "极速" in sname:
        extra60 = math.floor((((2*92 + 31 + evs.get('speed',0)//4) * 0.6 + 5) * 1.1)) + 60
        print(f"  (若+60速: {extra60})")
