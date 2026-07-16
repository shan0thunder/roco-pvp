#!/usr/bin/env python3
"""Fast parallel WebP conversion"""
import os, sys, time
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

IMG_DIR = "data/images"

def convert_one(fname):
    src = os.path.join(IMG_DIR, fname)
    webp_name = fname.rsplit(".", 1)[0] + ".webp"
    dst = os.path.join(IMG_DIR, webp_name)
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        return ("skip", fname, 0, 0)
    try:
        img = Image.open(src).convert("RGBA")
        img.save(dst, "WEBP", quality=80, method=4)
        png_sz = os.path.getsize(src)
        webp_sz = os.path.getsize(dst)
        return ("ok", fname, png_sz, webp_sz)
    except Exception as e:
        return ("fail", fname, 0, str(e))

def main():
    pngs = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(".png")]
    total = len(pngs)
    done = sum(1 for f in os.listdir(IMG_DIR) if f.lower().endswith(".webp"))
    print(f"总计 {total} 张PNG, 已转换 {done} 张WebP")

    todo = [f for f in pngs if not os.path.exists(os.path.join(IMG_DIR, f.rsplit('.',1)[0]+'.webp'))]
    print(f"还需转换 {len(todo)} 张\n")

    if not todo:
        print("全部已完成!")
        return

    start = time.time()
    ok = skip = fail = 0
    total_png_sz = 0
    total_webp_sz = 0

    # 并行处理
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(convert_one, f): f for f in todo}
        for i, fut in enumerate(as_completed(futures), 1):
            status, fname, s1, s2 = fut.result()
            if status == "ok":
                ok += 1
                total_png_sz += s1
                total_webp_sz += s2
            elif status == "skip":
                skip += 1
            else:
                fail += 1

            if i % 20 == 0 or i == len(todo):
                pct = i / len(todo) * 100
                elapsed = time.time() - start
                print(f"  [{i}/{len(todo)}] {pct:.0f}%  ({elapsed:.0f}s)")

    elapsed = time.time() - start
    total_png = sum(os.path.getsize(os.path.join(IMG_DIR, f)) for f in os.listdir(IMG_DIR) if f.lower().endswith(".png"))
    total_webp = sum(os.path.getsize(os.path.join(IMG_DIR, f)) for f in os.listdir(IMG_DIR) if f.lower().endswith(".webp"))

    print(f"\n✅ 完成! 耗时 {elapsed:.0f}s")
    print(f"   新增转换: {ok}, 跳过: {skip}, 失败: {fail}")
    print(f"   PNG: {total_png/1024/1024:.0f}MB")
    print(f"   WebP: {total_webp/1024/1024:.0f}MB")
    print(f"   节省: {(1-total_webp/total_png)*100:.0f}%")

if __name__ == "__main__":
    main()
