#!/usr/bin/env python3
with open('d:/桌面/目录/洛克PVP/editor/editor.js', 'r', encoding='utf-8') as f:
    c = f.read()

# Add cacheImage method before _esc
old_esc = "  _esc(str) {"
new_method = '''  cacheImage(name) {
    const pet = this._data?.pets.find(p => p.name === name);
    if (!pet || !pet.image) return;
    const url = pet.image;
    const imgName = name.replace(/[\\\\s\\\\/\\\\?]/g, '_');
    fetch('/cache-image', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url, name: imgName})
    }).then(r => r.json()).then(data => {
      if (data.local_url) {
        pet.image = window.location.origin + data.local_url;
        document.getElementById('edit-image').value = pet.image;
        document.querySelector('.edit-image-preview').src = pet.image;
        document.getElementById('saveStatus').textContent = '\\\\u56FE\\\\u7247\\\\u5DF2\\\\u7F13\\\\u5B58';
      }
    }).catch(e => {
      document.getElementById('saveStatus').textContent = '\\\\u7F13\\\\u5B58\\\\u5931\\\\u8D25';
    });
  },

  _esc(str) {'''

c = c.replace(old_esc, new_method)

with open('d:/桌面/目录/洛克PVP/editor/editor.js', 'w', encoding='utf-8') as f:
    f.write(c)
print('Added cacheImage method')
