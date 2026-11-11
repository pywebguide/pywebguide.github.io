"""Версия кэша и список предзагрузки для sw.js.

Версия — хеш всех файлов сайта: изменили страницу, стиль или скрипт — версия другая,
браузер ставит новый service worker, и он удаляет кэш прошлой версии.

    python tools/build_sw.py           # вписать VERSION и PRECACHE в sw.js
    python tools/build_sw.py --check   # проверить, что sw.js актуален (для CI)
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".github", "tools", "docs", "examples", "pagefind", "node_modules", "__pycache__"}
# Не публикуются (см. .github/workflows/pages.yml): их правка не должна менять версию кэша
SKIP_FILES = {"sw.js", "README.txt", ".gitignore"}

# Предзагрузка: всё, без чего не работают уже открытые страницы. Картинки и шрифты кэшируются при первом показе
CORE = ["styles.css", "script.js", "features.js", "assets/i18n.js", "assets/checker.py",
        "assets/icon.svg", "assets/icon-192.png", "manifest.webmanifest"]


def site_files():
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if path.is_file() and not (set(rel.parts) & SKIP_DIRS) and rel.as_posix() not in SKIP_FILES:
            yield rel.as_posix()


def build():
    digest = hashlib.sha256()
    for rel in site_files():
        digest.update(rel.encode())
        digest.update((ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    pages = [rel for rel in site_files() if rel.endswith(".html") and rel != "404.html"]
    precache = ["/", "/kk/", "/en/"] + ["/" + rel for rel in pages] + ["/" + rel for rel in CORE]
    text = (ROOT / "sw.js").read_text(encoding="utf-8")
    text = re.sub(r'const VERSION = "[^"]*";', f'const VERSION = "pyweb-{digest.hexdigest()[:10]}";', text, count=1)
    text = re.sub(r"const PRECACHE = \[.*?\];", "const PRECACHE = " + json.dumps(precache, ensure_ascii=False) + ";", text, count=1, flags=re.S)
    return text


def main():
    new = build()
    current = (ROOT / "sw.js").read_text(encoding="utf-8")
    if "--check" in sys.argv:
        if new != current:
            print("sw.js устарел: запустите python tools/build_sw.py")
            sys.exit(1)
        print("sw.js актуален")
        return
    (ROOT / "sw.js").write_text(new, encoding="utf-8", newline="\n")
    print(re.search(r'const VERSION = "([^"]*)"', new).group(1))


if __name__ == "__main__":
    main()
