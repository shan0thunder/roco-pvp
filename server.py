"""
本地开发服务器
一键启动: python server.py
"""

import http.server
import socketserver
import webbrowser
import sys
import os
import json
from pathlib import Path
import shutil
from datetime import datetime

project_dir = Path(__file__).parent
os.chdir(project_dir)

PORT = 8080
DATA_PATH = project_dir / "data" / "product" / "product_data.json"
PETS_PATH = project_dir / "data" / "pets.json"
BACKUP_DIR = project_dir / "data" / "backup"

def _load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def _save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)

        try:
            if self.path == '/save-data':
                self._handle_save_all(body)
            elif self.path == '/save-pet':
                self._handle_save_pet(body)
            elif self.path == '/cache-image':
                self._handle_cache_image(body)
            elif self.path == '/save-skills':
                self._handle_save_skills(body)
            else:
                self._send_json(404, {"status": "error", "message": "not found"})
        except Exception as e:
            self._send_json(500, {"status": "error", "message": str(e)})

    def _handle_save_all(self, body):
        data = json.loads(body)
        # 自动备份
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if DATA_PATH.exists():
            shutil.copy2(DATA_PATH, BACKUP_DIR / f"product_{ts}.json")

        _save_json(DATA_PATH, data)
        _save_json(PETS_PATH, data.get("pets", []))
        self._send_json(200, {"status": "ok", "pets_count": len(data.get("pets", []))})

    def _handle_save_pet(self, body):
        """增量保存单个精灵"""
        update = json.loads(body)
        name = update.get("name", "")
        if not name:
            self._send_json(400, {"status": "error", "message": "missing name"})
            return

        product = _load_json(DATA_PATH)
        pets = product.get("pets", [])
        found = False
        for i, p in enumerate(pets):
            if p["name"] == name:
                pets[i] = {**p, **update}
                found = True
                break
        if not found:
            pets.append(update)
        product["pets"] = pets
        _save_json(DATA_PATH, product)
        _save_json(PETS_PATH, pets)
        self._send_json(200, {"status": "ok", "pet": name})

    def _handle_save_skills(self, body):
        """批量更新技能（修改所有精灵的同名技能）"""
        updates = json.loads(body)
        if not isinstance(updates, list):
            updates = [updates]

        product = _load_json(DATA_PATH)
        pets = product.get("pets", [])
        update_count = 0

        for update in updates:
            skill_name = update.get("name", "")
            if not skill_name:
                continue
            for p in pets:
                for s in p.get("skills", []):
                    if s["name"] == skill_name:
                        s.update(update)
                        update_count += 1
                        break

        product["pets"] = pets
        _save_json(DATA_PATH, product)
        _save_json(PETS_PATH, pets)
        self._send_json(200, {"status": "ok", "updated": update_count})

    def _handle_cache_image(self, body):
        import urllib.request
        data = json.loads(body)
        url = data.get("url", "")
        name = data.get("name", "image")
        if not url:
            self._send_json(400, {"status": "error", "message": "missing url"})
            return
        img_dir = project_dir / "data" / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        ext = url.split(".")[-1].split("?")[0] or "png"
        fname = f"{name}.{ext}"
        fpath = img_dir / fname
        try:
            urllib.request.urlretrieve(url, fpath)
            local_url = f"/data/images/{fname}"
            self._send_json(200, {"status": "ok", "local_url": local_url})
        except Exception as e:
            self._send_json(500, {"status": "error", "message": str(e)})

    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))


def check_data():
    if not DATA_PATH.exists():
        print("=" * 50)
        print("  产品数据未找到！")
        print("  请先运行: python scraper/cli.py export-product")
        print("=" * 50)
        return False
    size_kb = DATA_PATH.stat().st_size / 1024
    print(f"  数据文件: {DATA_PATH} ({size_kb:.0f} KB)")
    return True

def main():
    print()
    print("=" * 50)
    print("  洛·世界PVP工具箱 - 开发服务器")
    print("=" * 50)
    print()

    if not check_data():
        sys.exit(1)

    print(f"  访问地址: http://localhost:{PORT}/frontend/")
    print(f"  编辑器:  http://localhost:{PORT}/editor/editor.html")
    print(f"  按 Ctrl+C 停止")
    print()

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"  服务器已启动: http://localhost:{PORT}/frontend/")
        print()
        try:
            webbrowser.open(f"http://localhost:{PORT}/frontend/")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  服务器已停止")
            httpd.shutdown()

if __name__ == "__main__":
    main()
