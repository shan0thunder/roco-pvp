#!/usr/bin/env python3
"""
重新理解: 有"+60"=加点60, 无标注=加点0
"""
import math

# 用户数据: (名称, 种族速, 速度加点, 性格, 最终速)
data = [
    ("火焰猿",   60, 0,   1.0, 126),
    ("烈火守护", 65, 0,   0.9, 124),   # 性格-速度
    ("奇丽花",   80, 60,  1.0, 184),
    ("尖嘴狐仙", 100, 0,  0.9, 158),   # 性格-速度
    ("翠顶夫人", 115, 0,  1.0, 187),
    ("火神",     130, 60, 1.1, 273),    # 性格+速度
]

print("="*70)
print("反推60级无加点时的公式: f(种族值) → 最终速")
print("="*70)

# 先看无加点、无性格的 (base only)
for name, base, bonus, nature, result in data:
    if bonus == 0 and nature == 1.0:
        print(f"\n{name}: 种族值{base} → {result}  (提升{result-base})")
    elif bonus == 0:
        # 含性格, 需要反推中性值
        # 尝试: 性格是×0.9/×1.1? 还是 +10%/ -10% 基数?
        for method in ['×nature', '+base×0.1', '-base×0.1']:
            if method == '×nature':
                neutral = result / nature
            elif method == '+base×0.1' and nature > 1:
                neutral = result - base * 0.1
            elif method == '-base×0.1' and nature < 1:
                neutral = result + base * 0.1
            else:
                continue
            print(f"  若性格为{method}: 中性值≈{neutral:.1f} (提升{neutral-base:.1f})")

# 关键是: 60级无加点时, 种族值60→126, 115→187, 那80→? 130→?
# 线性假设: f(B) = B + 60 + ceil(B/10)
print("\n\n尝试公式: 60级无加点 = B + 60 + ceil(B/10)")
for name, base, bonus, nature, result in data:
    if bonus == 0 and nature == 1.0:
        v = base + 60 + math.ceil(base/10)
        print(f"  {name}: {base}+60+{math.ceil(base/10)}={v} vs 实际{result} {'✓' if v==result else '✗'}")

# 试试: 60级无加点 = floor(B × 1.1) + 60
print("\n\n尝试公式: 60级无加点 = floor(B × 1.1) + 60")
for name, base, bonus, nature, result in data:
    if bonus == 0 and nature == 1.0:
        v = math.floor(base * 1.1) + 60
        print(f"  {name}: floor({base}×1.1)+60={v} vs 实际{result} {'✓' if v==result else '✗'}")

# 试试 ceil
print("\n\n尝试公式: 60级无加点 = ceil(B × 1.1) + 60")
for name, base, bonus, nature, result in data:
    if bonus == 0 and nature == 1.0:
        v = math.ceil(base * 1.1) + 60
        print(f"  {name}: ceil({base}×1.1)+60={v} vs 实际{result} {'✓' if v==result else '✗'}")

# 看看加入加点后怎么算
print("\n\n尝试加点后的公式 (以奇丽花和火神验证)")
# 奇丽花: 80+60加点=184, 中性
# 如果公式是 (B+加点)×K + C ?

print("\n方案A: 加点前公式 → (B + 60 + ceil(B/10)) + 加点")
for name, base, bonus, nature, result in data:
    base_val = base + 60 + math.ceil(base/10)
    # 性格怎么处理?
    if nature == 1.0:
        v = base_val + bonus
    elif nature == 1.1:
        # +speed: 也加?
        v = math.floor((base_val + bonus) * nature)
    else:
        v = math.floor((base_val + bonus) * 0.9)
    print(f"  {name}: ({base}+60+{math.ceil(base/10)})+{bonus}={base_val+bonus} ×{nature:3.1f} → {v} vs 实际{result} {'✓' if v==result else '✗'}")

# 方案B: 加点直接在公式里加
print("\n方案B: 加点作为公式内加法 → (B + 60 + ceil(B/10) + 加点) × 性格")
for name, base, bonus, nature, result in data:
    base_val = base + 60 + math.ceil(base/10) + bonus
    v = math.floor(base_val * nature)
    print(f"  {name}: ({base}+60+{math.ceil(base/10)}+{bonus})={base_val} ×{nature:3.1f} → {v} vs 实际{result} {'✓' if v==result else '✗'}")

# 方案C: 加点和基础一起参与ceil
print("\n方案C: 加点随基础 → B + 60 + ceil((B+加点)/10)")
for name, base, bonus, nature, result in data:
    base_val = base + 60 + math.ceil((base+bonus)/10)
    v = math.floor(base_val * nature)
    print(f"  {name}: {base}+60+ceil({base+bonus}/10)={base_val} ×{nature:3.1f} → {v} vs 实际{result} {'✓' if v==result else '✗'}")

# 方案D: 按比例成长
print("\n方案D: f(B) = B × 2.1 (对60→126), f(B) = B × 1.626 (对115→187)")
print("     不成立! 成长率不是常数!")
