#!/usr/bin/env python3
"""Convert pet images to WebP format for faster loading"""
import os
from PIL import Image

img_dir = "data/images"
converted = 0
skipped = 0

for fname in os.listdir(img_dir):
    if not fname.lower().endswith(".png"):
        continue
    src = os.path.join(img_dir, fname)
    webp_name = fname.rsplit(".", 1)[0] + ".webp"
    dst = os.path.join(img_dir, webp_name)

    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        skipped += 1
        continue

    try:
        img = Image.open(src).convert("RGBA")
        img.save(dst, "WEBP", quality=80, method=6)
        # Show size comparison
        png_size = os.path.getsize(src)
        webp_size = os.path.getsize(dst)
        saved = (1 - webp_size/png_size) * 100
        converted += 1
        if converted <= 3 or converted % 50 == 0:
            print(f"  [{converted}] {fname}: {png_size//1024}KB → {webp_size//1024}KB ({saved:.0f}% saved)")
    except Exception as e:
        print(f"  FAIL: {fname} - {e}")

# Summary
total_png = sum(1 for f in os.listdir(img_dir) if f.lower().endswith(".png"))
total_webp = sum(1 for f in os.listdir(img_dir) if f.lower().endswith(".webp"))
png_size = sum(os.path.getsize(os.path.join(img_dir, f)) for f in os.listdir(img_dir) if f.lower().endswith(".png"))
webp_size = sum(os.path.getsize(os.path.join(img_dir, f)) for f in os.listdir(img_dir) if f.lower().endswith(".webp"))

print(f"\n✅ 完成: 转换 {converted}, 跳过 {skipped}")
print(f"   PNG: {total_png} 张, {png_size/1024/1024:.0f}MB")
print(f"   WebP: {total_webp} 张, {webp_size/1024/1024:.0f}MB")
print(f"   节省: {(1-webp_size/png_size)*100:.0f}%")
