#!/usr/bin/env python3
import json, urllib.request, os, time, re

d = json.load(open('data/product/product_data.json', 'rb'))
pets = d['pets']
with_img = [p for p in pets if p.get('image')]
print(f'Total: {len(pets)} pets, {len(with_img)} with images')
os.makedirs('data/images', exist_ok=True)

success = 0
failed = 0
for i, p in enumerate(with_img):
    url = p['image']
    name = p['name']
    safe_name = re.sub(r'[\\\/\?\:\*\"\<\>\|]', '_', name)
    ext = 'png'
    if '.jpg' in url.lower() or '.jpeg' in url.lower():
        ext = 'jpg'
    elif '.webp' in url.lower():
        ext = 'webp'
    elif '.gif' in url.lower():
        ext = 'gif'
    fname = f"{safe_name}.{ext}"
    fpath = os.path.join('data/images', fname)

    if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
        p['image'] = f'/data/images/{fname}'
        success += 1
        continue

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            with open(fpath, 'wb') as f:
                f.write(resp.read())
        p['image'] = f'/data/images/{fname}'
        success += 1
    except Exception as e:
        failed += 1
        if failed <= 3:
            print(f'FAIL [{i+1}]: {name} -> {str(e)[:60]}')

    if (i+1) % 100 == 0:
        print(f'  [{i+1}/{len(with_img)}] {success} OK, {failed} FAIL')
    time.sleep(0.05)

# Save updated data
d['pets'] = pets
with open('data/product/product_data.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
with open('data/pets.json', 'w', encoding='utf-8') as f:
    json.dump(pets, f, ensure_ascii=False, indent=2)

total_size = sum(os.path.getsize(os.path.join('data/images', f)) for f in os.listdir('data/images') if os.path.isfile(os.path.join('data/images', f)))
print(f'\nDone: {success} cached, {failed} failed')
print(f'Images dir: {total_size/1024:.0f} KB')
