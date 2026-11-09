"""Полный код первого проекта лежит в examples/ и совпадает с кодом на странице project.html.

Источник правды — страница: из её блоков кода берутся финальные версии файлов
(Flask: шаг 5, Django: шаги 3, 7, 8, 9). Файлы, которых на странице нет (settings.py,
миграции, тесты), созданы командами django-admin/makemigrations и лежат в examples/ как есть.

    python tools/sync_examples.py           # обновить examples/ и архивы *.zip
    python tools/sync_examples.py --check   # только проверить совпадение (для CI)
"""
import html
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"

# Подпись блока на странице -> файл в примере. Берётся последний блок с такой подписью в разделе.
FLASK = {"app.py": "app.py"}
DJANGO = {
    "tasks/models.py": "tasks/models.py",
    "tasks/admin.py": "tasks/admin.py",
    "tasks/forms.py": "tasks/forms.py",
    "tasks/views.py": "tasks/views.py",
    "mysite/urls.py": "mysite/urls.py",
    "tasks/templates/tasks/index.html": "tasks/templates/tasks/index.html",
}


def blocks(section_html):
    found = {}
    for label, code in re.findall(r'<div class="code-head">\s*<span>([^<]+)</span>.*?<pre><code>(.*?)</code></pre>', section_html, flags=re.S):
        found[label] = html.unescape(code) + "\n"
    return found


def expected():
    page = (ROOT / "project.html").read_text(encoding="utf-8")
    flask_part = page[page.index('id="flask"'):page.index('id="django"')]
    django_part = page[page.index('id="django"'):page.index('id="errors"')]
    files = {}
    for label, target in FLASK.items():
        files[f"flask-todo/{target}"] = blocks(flask_part)[label]
    for label, target in DJANGO.items():
        files[f"django-todo/{target}"] = blocks(django_part)[label]
    return files


def pack(name):
    folder = EX / name
    archive = EX / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(folder.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".sqlite3", ".db", ".pyc"):
                # Фиксированная дата: архив не меняется, если не менялись файлы
                info = zipfile.ZipInfo(f"{name}/{path.relative_to(folder).as_posix()}", date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, path.read_bytes().replace(b"\r\n", b"\n"))


def main():
    check = "--check" in sys.argv
    stale = []
    for rel, text in expected().items():
        path = EX / rel
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.exists() else None
        if current != text:
            stale.append(rel)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8", newline="\n")
    if check:
        if stale:
            print("Код в examples/ отличается от project.html. Запустите python tools/sync_examples.py:")
            print("\n".join("  " + s for s in stale))
            sys.exit(1)
        print("examples/ совпадает с project.html")
        return
    for name in ("flask-todo", "django-todo"):
        pack(name)
    print(f"Обновлено файлов: {len(stale)}, архивы собраны")


if __name__ == "__main__":
    main()
