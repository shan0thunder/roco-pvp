#!/usr/bin/env python3
"""
洛克王国世界 — 正确公式推导
已知: 种族值固定, 60级的加成是(+60), 加点(0-60/项, 可加3项), 性格(±10%)
"""
import math

# 用户提供的PVP数据 (全是60级)
# "+60" 标注表示"60级"而不是60点分配
examples = [
    # (名称, 种族速, 性格, 最终速, 备注)
    ("火焰猿",   60,  1.0, 126, ""),
    ("烈火守护", 65,  0.9, 124, "性格-速"),
    ("奇丽花",   80,  1.0, 184, ""),
    ("尖嘴狐仙", 100, 0.9, 158, "性格-速"),
    ("翠顶夫人", 115, 1.0, 187, ""),
    ("火神",     130, 1.1, 273, "性格+速"),
]

print("="*80)
print("验证公式: 最终速 = floor((种族值 + 60 + 加点) × 性格)")
print("其中 60=等级加成, 加点=玩家分配(0-60)")
print("="*80)

# 反推每个精灵在速度上的加点
for name, base, nature, result, note in examples:
    # (base + 60 + X) × nature → result
    # X = result/nature - base - 60
    # 由于floor, 需要找精确整数X
    for x in range(0, 61):
        v = math.floor((base + 60 + x) * nature)
        if v == result:
            print(f"\n  {name:6s}(base={base:3d}) +60级 +加点{x:2d} = {base+60+x:3d} ×{nature} → {v:3d} ✓")
            if x > 0:
                print(f"          → 反推: {name}在速度上分配了加点{x}")
            break
    else:
        # 近似值
        for x in range(0, 61):
            v = math.floor((base + 60 + x) * nature)
            if abs(v - result) <= 2:
                print(f"  {name:6s}(base={base:3d}): 最近加点{x:2d} → {v:3d} (偏差{v-result})")
                break

print("\n" + "="*80)
print("迪莫速度计算 (种族速=92, 性格+速×1.1)")
print("加点分配: 物攻+6, 魔攻+6 → 不加到速度上")
print("="*80)

base = 92
nature = 1.1

print(f"\n迪莫速度 = floor((92 + 60 + 速度加点) × 1.1)")
print(f"\n不同加点方案:")
for x in [0, 30, 51, 60]:
    v = math.floor((base + 60 + x) * nature)
    print(f"  速度加点={x:2d}: ({base}+60+{x})={base+60+x:3d} ×1.1 → {v:3d}")

print(f"\n你实测的223: floor((92+60+{51})×1.1)=floor(203×1.1)=223 ✓ (加点51 → ≈60)")

# ===== 迪莫完整属性 =====
print("\n" + "="*80)
print("迪莫 60级 完整属性 (加点物攻+6, 魔攻+6, 性格天真)")
print("="*80)

# 迪莫全种族值
pets = [
    ("生命", 120, 1.0),
    ("物攻",  80, 1.0),
    ("物防", 105, 1.0),
    ("魔攻",  80, 1.0),
    ("魔防", 105, 0.9),
    ("速度",  92, 1.1),
]

bonus = {'物攻': 6, '魔攻': 6}

# 方案1: 只加双攻各6, 其余不加
print("\n--- 方案A: 只加物攻+6, 魔攻+6, 速度0 ---")
for label, base, nature in pets:
    x = bonus.get(label, 0)
    v = math.floor((base + 60 + x) * nature)
    print(f"  {label:6s}: ({base:3d}+60+{x})={base+60+x:3d} ×{nature} → {v:3d}")

# 方案2: 把可分配的180点分给三个属性
print("\n--- 方案B: 物攻+60, 魔攻+60, 速度+60 (三项满加)---")
for label, base, nature in pets:
    x = 60 if label in ['物攻','魔攻','速度'] else 0
    v = math.floor((base + 60 + x) * nature)
    print(f"  {label:6s}: ({base:3d}+60+{x})={base+60+x:3d} ×{nature} → {v:3d}")

# 方案3: 物攻+60, 魔攻+6, 速度+60
print("\n--- 方案C: 物攻+60, 魔攻+6, 速度+60 ---")
for label, base, nature in pets:
    x = 60 if label in ['物攻','速度'] else bonus.get(label, 0)
    v = math.floor((base + 60 + x) * nature)
    print(f"  {label:6s}: ({base:3d}+60+{x})={base+60+x:3d} ×{nature} → {v:3d}")

# 方案4: 你实测的PVP数据 (速度加点约51, 物攻魔攻未知)
print("\n--- 方案D: 速度加点51 (对应你实测223), 物攻+6, 魔攻+6 ---")
for label, base, nature in pets:
    if label == '速度':
        x = 51
    else:
        x = bonus.get(label, 0)
    v = math.floor((base + 60 + x) * nature)
    print(f"  {label:6s}: ({base:3d}+60+{x})={base+60+x:3d} ×{nature} → {v:3d}")
