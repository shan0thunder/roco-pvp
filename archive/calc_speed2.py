#!/usr/bin/env python3
"""
速度公式精确反推 — 以IV=31(满个体)为前提, 倒推每只精灵的EV投入
"""
import math

examples = [
    # (名称, 种族值, 性格倍率, 最终速度)
    ("火焰猿",   60,  1.0, 126),
    ("烈火守护", 65,  0.9, 124),
    ("奇丽花",   80,  1.0, 184),
    ("尖嘴狐仙", 100, 0.9, 158),
    ("翠顶夫人", 115, 1.0, 187),
    ("火神",     130, 1.1, 273),
]

LV = 60

print("="*90)
print("速度公式反推 (假设IV=31满个体, 倒推EV)")
print("公式: Speed = floor(((2×B + 31 + EV/4) × Lv/100 + 5) × Nature)")
print("="*90)

for name, base, nature, target in examples:
    print(f"\n--- {name} (base={base}, nature={nature}) 目标={target} ---")
    # 找EV
    found = []
    for ev in range(0, 256, 4):
        raw = ((2*base + 31 + ev//4) * LV / 100) + 5
        v = math.floor(raw * nature)
        if v == target:
            found.append(ev)
    if found:
        print(f"  ✓ 匹配! 努力值(EV)可选: {found}")
        opt_ev = found[0] if found else 0
        neutral = ((2*base + 31 + opt_ev//4) * LV / 100) + 5
        print(f"     中性值 ≈ {neutral:.1f}, 性格后 = {math.floor(neutral*nature)}")
    else:
        # 最近值
        best_ev = None
        best_v = 0
        for ev in range(0, 256, 4):
            raw = ((2*base + 31 + ev//4) * LV / 100) + 5
            v = math.floor(raw * nature)
            if best_ev is None or abs(v-target) < abs(best_v-target):
                best_ev = ev
                best_v = v
        print(f"  ✗ 无完全匹配! 最近: EV={best_ev} → {best_v} (偏差{best_v-target})")

# 火神和奇丽花对不上 — 可能是有额外的+60速分配
print("\n" + "="*90)
print("尝试解释火神/奇丽花的额外60点速:")
print("假设: 最终速 = 标准公式结果 + 潜能分配60点")
print("="*90)

for name, base, nature, target in examples:
    # 假设公式结果 + 60 = 最终
    without_60 = target - 60 if target > 150 else target  # 仅对高值尝试
    if without_60 <= 0:
        without_60 = target

    print(f"\n--- {name} (base={base}) ---")
    print(f"  目标={target}")

    # 如果目标-60后, 再套公式
    adjusted = target - 60
    if adjusted > 0:
        found = []
        for ev in range(0, 256, 4):
            raw = ((2*base + 31 + ev//4) * LV / 100) + 5
            v = math.floor(raw * nature)
            if v == adjusted:
                found.append(ev)
        if found:
            print(f"  ✓ 若+60为潜能分配: 公式目标={adjusted}, EV={found}")
            print(f"    则总速度 = {adjusted} + 60 = {target}")
        else:
            # 找最近的
            best_ev = None
            best_v = 0
            for ev in range(0, 256, 4):
                raw = ((2*base + 31 + ev//4) * LV / 100) + 5
                v = math.floor(raw * nature)
                if best_ev is None or abs(v-adjusted) < abs(best_v-adjusted):
                    best_ev = ev
                    best_v = v
            print(f"  最近: EV={best_ev} → 公式值={best_v}, +60后={best_v+60} (偏差{best_v+60-target})")
