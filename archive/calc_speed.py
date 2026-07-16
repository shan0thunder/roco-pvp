#!/usr/bin/env python3
"""
洛克王国世界 — 速度值反推计算器
根据用户提供的PVP实况数据，反推正确的计算公式
"""
import json, math

# ===== 用户提供的PVP实况数据 =====
# 格式: (名称, 速度种族值, 性格修正, 最终速度, 说明)
examples = [
    ("火神",      130, 1.1, 273, "性格+速度"),
    ("烈火守护",   65, 0.9, 124, "性格-速度"),
    ("火焰猿",     60, 1.0, 126, "无性格修正"),
    ("翠顶夫人",  115, 1.0, 187, "无性格修正"),
    ("尖嘴狐仙",  100, 0.9, 158, "性格-速度"),
    ("奇丽花",     80, 1.0, 184, "无性格修正"),
]

print("=" * 80)
print("速度公式反推 — 精灵级别均为60级")
print("=" * 80)

# ========== 方案1: 宝可梦标准公式 ==========
# Speed = floor(((2*B + IV + EV/4) * Lv/100 + 5) * Nature)
print("\n" + "="*80)
print("【方案1】标准宝可梦公式: Speed = ((2×B + IV + EV/4)×Lv/100 + 5)×Nature")
print("="*80)

def calc_pokemon(base, iv, ev, nature, lv=60):
    raw = ((2 * base + iv + ev // 4) * lv / 100) + 5
    return math.floor(raw * nature)

# 对每个例子, 找最合适的IV+EV组合
for name, base, nature, result, note in examples:
    print(f"\n  {name}(base={base}, {note}): 目标={result}")
    # IV从0-31, EV从0-252(4的倍数)
    best = None
    best_diff = 999
    for iv in range(0, 32):
        for ev in range(0, 256, 4):
            v = calc_pokemon(base, iv, ev, nature)
            diff = abs(v - result)
            if diff < best_diff:
                best_diff = diff
                best = (iv, ev, v)
    print(f"    最佳匹配: IV={best[0]}, EV={best[1]}, 计算值={best[2]}, 偏差={best_diff}")
    # 也展示IV=31时需要的EV
    for ev in range(0, 256, 4):
        v = calc_pokemon(base, 31, ev, nature)
        if v == result:
            print(f"    [IV=31方案] EV={ev} → {v} ✓")
            break
        elif abs(v - result) <= 1:
            print(f"    [IV=31近似] EV={ev} → {v} (偏差{abs(v-result)})")

# ========== 方案2: 加Level项 ==========
# Speed = floor(((2*B + IV + EV/4) * Lv/100 + Lv/10 + 5) * Nature)
print("\n" + "="*80)
print("【方案2】+Level调整: Speed = ((2×B + IV + EV/4)×Lv/100 + Lv/10 + 5)×Nature")
print("="*80)

def calc_v2(base, iv, ev, nature, lv=60):
    raw = ((2 * base + iv + ev // 4) * lv / 100) + lv/10 + 5
    return math.floor(raw * nature)

for name, base, nature, result, note in examples:
    print(f"\n  {name}(base={base}): 目标={result}")
    best = None
    best_diff = 999
    for iv in range(0, 32):
        for ev in range(0, 256, 4):
            v = calc_v2(base, iv, ev, nature)
            diff = abs(v - result)
            if diff < best_diff:
                best_diff = diff
                best = (iv, ev, v)
    print(f"    最佳: IV={best[0]}, EV={best[1]}, 计算值={best[2]}, 偏差={best_diff}")

# ========== 方案3: 简化中式公式 ==========
# Speed = floor((Base*2 + 天赋) * Lv/100 * Nature) + Lv + 5
print("\n" + "="*80)
print("【方案3】中式简化: Speed = floor((2×B + 天赋) × Lv/100 × Nature) + Lv + 5")
print("="*80)

def calc_v3(base, talent, nature, lv=60):
    raw = (2 * base + talent) * lv / 100 * nature
    return math.floor(raw) + lv + 5

for name, base, nature, result, note in examples:
    print(f"\n  {name}(base={base}): 目标={result}")
    best = None
    best_diff = 999
    for talent in range(0, 101):  # 天赋可能范围更大
        v = calc_v3(base, talent, nature)
        diff = abs(v - result)
        if diff < best_diff:
            best_diff = diff
            best = (talent, v)
    print(f"    最佳: 天赋={best[0]}, 计算值={best[1]}, 偏差={best_diff}")

# ========== 方案4: 线性公式 ==========
# Speed = floor(B × A + B) × Nature, 由实际数据拟合
print("\n" + "="*80)
print("【方案4】线性拟合 — 由无性格修正精灵拟合直线")
print("="*80)
# 用火焰猿(60→126)和翠顶夫人(115→187)拟合
# y = kx + b
x1, y1 = 60, 126
x2, y2 = 115, 187
k = (y2 - y1) / (x2 - x1)
b = y1 - k * x1
print(f"  拟合: Speed_neutral = Base × {k:.6f} + {b:.6f}")

for name, base, nature, result, note in examples:
    neutral = base * k + b
    v = math.floor(neutral * nature)
    print(f"  {name}(base={base}, nature={nature}): 中性={neutral:.1f} → 最终={v}, 目标={result} {'✓' if v==result else '✗'}")

# ========== 方案5: 直接乘系数 ==========
print("\n" + "="*80)
print("【方案5】Speed = ceil(Base × 1.1) + Lv  (Lv=60)")
print("="*80)

for name, base, nature, result, note in examples:
    v = math.ceil(base * 1.1) + 60
    v2 = math.floor(v * nature) if nature != 1.0 else v
    if nature > 1.0:
        v2 = math.floor(v * nature)
    elif nature < 1.0:
        v2 = math.ceil(v * nature)
    else:
        v2 = v
    print(f"  {name}: {v}(中性) ×{nature} → {v2}, 目标={result} {'✓' if v2==result else '✗'}")

# 考虑性格影响在公式内部的方式不同
print("\n" + "="*80)
print("【方案5b】Speed = ceil(Base × Nature × 1.1) + 60")
print("="*80)
for name, base, nature, result, note in examples:
    v = math.ceil(base * nature * 1.1) + 60
    print(f"  {name}: 计算={v}, 目标={result} {'✓' if v==result else '✗'}")

print("\n" + "="*80)
print("【方案5c】Speed = (ceil(Base × 1.1) + 60) × Nature → floor")
print("="*80)
for name, base, nature, result, note in examples:
    v = math.floor((math.ceil(base * 1.1) + 60) * nature)
    print(f"  {name}: 计算={v}, 目标={result} {'✓' if v==result else '✗'}")

print("\n" + "="*80)
print("【方案5d】Speed = ceil(Base × 1.1 + 60) × Nature → floor")
print("="*80)
for name, base, nature, result, note in examples:
    v = math.floor(math.ceil(base * 1.1 + 60) * nature)
    print(f"  {name}: 计算={v}, 目标={result} {'✓' if v==result else '✗'}")
