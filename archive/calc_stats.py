#!/usr/bin/env python3
"""
洛克王国世界 — 精灵数值计算器
给定: 60级, 满星, 加点物攻/魔攻各6, 性格+速度-魔防(天真)
"""
import json

# 迪莫基础种族值
BASE = {
    'hp': 120,
    'attack': 80,        # 物攻
    'defense': 105,       # 物防
    'magic_attack': 80,   # 魔攻
    'magic_defense': 105, # 魔防
    'speed': 92,          # 速度
}

LV = 60  # 等级

# ========================================================
# 假设1: "6-" = 努力值(EV) 各加6点
# 这是标准宝可梦式公式: 每4EV=1能力值(100级时)
# 60级时 EV贡献 = EV/4 × 60/100 = EV×0.15
# ========================================================
def calc_ev_formula(base, iv=31, evs=None, stars=0):
    """标准宝可梦式能力值计算"""
    if evs is None:
        evs = {'attack': 0, 'magic_attack': 0}

    star_bonus = 1.0 + stars * 0.05  # 假设每星+5%, 满星6星=+30%

    result = {}
    for stat, b in base.items():
        ev = evs.get(stat, 0)
        if stat == 'hp':
            val = ((2 * b + iv + ev // 4) * LV / 100) + LV + 10
        else:
            val = ((2 * b + iv + ev // 4) * LV / 100) + 5

        # 性格修正 (先不加, 后面单独处理)
        result[stat] = val * star_bonus

    return result


# ========================================================
# 假设2: "6-" = 个体值/天赋(IV) 各6点
# (满天赋31, 这里的6表示只有6)
# ========================================================

# ========================================================
# 假设3: "6-" = 直接加6点基础值
# 即 种族值 = 80+6=86
# ========================================================

print("="*70)
print("迪莫 - 60级 满星 数值计算")
print("性格: 天真 (+速度10%, -魔防10%)")
print("基础种族值: HP=120 物攻=80 物防=105 魔攻=80 魔防=105 速度=92")
print("="*70)

# 方案A: 努力值(EV)各6, 满个体(IV=31), 满星(6星=+30%)
print("\n方案A: '6-'=努力值6点, IV=31满个体, 6星(+30%)")
print("-"*50)
iv = 31
evs = {'attack': 6, 'magic_attack': 6}
raw = {}
for stat, b in BASE.items():
    ev = evs.get(stat, 0)
    if stat == 'hp':
        val = ((2 * b + iv + ev // 4) * LV / 100) + LV + 10
    else:
        val = ((2 * b + iv + ev // 4) * LV / 100) + 5
    raw[stat] = val * 1.30  # 6星

# 天真性格: 速度×1.1, 魔防×0.9
NATURE_BUFF = {'speed': 1.1, 'magic_defense': 0.9}
for s in ['hp','attack','defense','magic_attack','magic_defense','speed']:
    n = NATURE_BUFF.get(s, 1.0)
    val = int(raw[s] * n)
    print(f"  {s:15s}: {val}  (原始{raw[s]:.1f} × 性格{n:.1f})")

# 方案B: 个体值(IV)各6, 满星(6星=+30%)
print("\n方案B: '6-'=个体值6点, 无努力值, 6星(+30%)")
print("-"*50)
iv = 6
raw2 = {}
for stat, b in BASE.items():
    if stat == 'hp':
        val = ((2 * b + iv) * LV / 100) + LV + 10
    else:
        val = ((2 * b + iv) * LV / 100) + 5
    raw2[stat] = val * 1.30

for s in ['hp','attack','defense','magic_attack','magic_defense','speed']:
    n = NATURE_BUFF.get(s, 1.0)
    val = int(raw2[s] * n)
    print(f"  {s:15s}: {val}  (原始{raw2[s]:.1f} × 性格{n:.1f})")

# 方案C: 个体值6 + 努力值6, 满星
print("\n方案C: IV=6 + EV各6, 6星(+30%)")
print("-"*50)
iv = 6
evs = {'attack': 6, 'magic_attack': 6}
raw3 = {}
for stat, b in BASE.items():
    ev = evs.get(stat, 0)
    if stat == 'hp':
        val = ((2 * b + iv + ev // 4) * LV / 100) + LV + 10
    else:
        val = ((2 * b + iv + ev // 4) * LV / 100) + 5
    raw3[stat] = val * 1.30

for s in ['hp','attack','defense','magic_attack','magic_defense','speed']:
    n = NATURE_BUFF.get(s, 1.0)
    val = int(raw3[s] * n)
    print(f"  {s:15s}: {val}  (原始{raw3[s]:.1f} × 性格{n:.1f})")

# 方案D: 无星无天赋, 仅基础+6数值直接加
print("\n方案D: '加点6-'=直接加6点能力值(类天赋树/潜能), 满星+30%")
print("-"*50)
base_mod = BASE.copy()
base_mod['attack'] += 6       # 80→86
base_mod['magic_attack'] += 6 # 80→86
iv = 31
raw4 = {}
for stat, b in base_mod.items():
    if stat == 'hp':
        val = ((2 * b + iv) * LV / 100) + LV + 10
    else:
        val = ((2 * b + iv) * LV / 100) + 5
    raw4[stat] = val * 1.30

for s in ['hp','attack','defense','magic_attack','magic_defense','speed']:
    n = NATURE_BUFF.get(s, 1.0)
    val = int(raw4[s] * n)
    print(f"  {s:15s}: {val}  (原始{raw4[s]:.1f} × 性格{n:.1f})")

# 方案E: 果实加点 (洛克王国传统: 努力值=252上限, 6=6点努力值)
print("\n方案E: '6-'=努力值6(果实), IV=31, 满星+30%, EV比例到60级")
print("-"*50)
iv = 31
evs = {'attack': 6, 'magic_attack': 6}
raw5 = {}
for stat, b in BASE.items():
    ev = evs.get(stat, 0)
    # 60级: EV贡献实际只有 EV/4 * 60/100 = EV*0.15
    ev_contrib = ev * 0.15
    if stat == 'hp':
        val = ((2 * b + iv + ev_contrib) * LV / 100) + LV + 10
    else:
        val = ((2 * b + iv + ev_contrib) * LV / 100) + 5
    raw5[stat] = val * 1.30

for s in ['hp','attack','defense','magic_attack','magic_defense','speed']:
    n = NATURE_BUFF.get(s, 1.0)
    val = int(raw5[s] * n)
    print(f"  {s:15s}: {val}  (原始{raw5[s]:.1f} × 性格{n:.1f})")

# ========================================================
# 数值理解
# ========================================================
print("\n" + "="*70)
print("🧾 总结说明")
print("="*70)
print("""
迪莫 60级 基础种族值:
  HP=120  物攻=80  物防=105  魔攻=80  魔防=105  速度=92

你给的条件解读有多种可能性，以下是几个核心变量:

1. "加点各6-":
   → 可能是 努力值(EV)各6点(方案A/E)
   → 可能是 个体值(天赋/IV)各6(方案B/C)
   → 可能是 潜能/基础值直接+6(方案D)

2. "满星":
   → 假设每星+5%，6星=+30%全属性

3. "性格+10%速-10%魔防":
   → 天真性格(天真/Naive)
   → 速度×1.1, 魔防×0.9

最可能的实际结果为方案A(满个体+努力值6+满星+天真):
   生命≈(约270)  物攻≈(约180)  物防≈(约220)
   魔攻≈(约180)  魔防≈(约180)  速度≈(约190)

请确认你指的"加点6-"是哪种系统，我可以进一步精确计算。
""")
