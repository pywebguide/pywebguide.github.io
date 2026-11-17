"""Проверка снимков «Код после шага N» (examples/*/steps/step-N.zip, собирает tools/sync_examples.py).

Каждый архив распаковывается во временную папку — ровно то, что скачает ученик:
  Flask  — app.py импортируется без ошибок, главная страница отвечает 200;
  Django — python manage.py check без замечаний; если миграция уже есть (шаг 4 и дальше) —
           makemigrations --check (модели и миграции совпадают), migrate и, когда есть шаблон,
           главная страница отвечает 200.
Код выхода 1 при ошибках. Нужны Flask и Django из tools/requirements.txt.
"""
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"
PY = sys.executable

FLASK_PROBE = """
import app
response = app.app.test_client().get("/")
assert response.status_code == 200, response.status_code
assert "Мои задачи" in response.get_data(as_text=True)
"""

DJANGO_PROBE = """
from django.test import Client
from django.test.utils import setup_test_environment
setup_test_environment()
response = Client().get("/")
assert response.status_code == 200, response.status_code
assert "Мои задачи" in response.content.decode()
"""


def run(folder, *args):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([PY, *args], cwd=folder, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
    return result.returncode, (result.stdout + result.stderr).strip()


def check_flask(folder):
    return [run(folder, "-c", FLASK_PROBE) + ("импорт app.py и GET /",)]


def check_django(folder):
    results = [run(folder, "manage.py", "check") + ("manage.py check",)]
    if (folder / "tasks" / "migrations" / "0001_initial.py").exists():
        results.append(run(folder, "manage.py", "makemigrations", "--check", "--dry-run") + ("makemigrations --check",))
        results.append(run(folder, "manage.py", "migrate", "-v", "0") + ("migrate",))
        if (folder / "tasks" / "templates").exists():
            results.append(run(folder, "manage.py", "shell", "-c", DJANGO_PROBE) + ("GET /",))
    return results


def main():
    archives = sorted(EX.glob("*/steps/step-*.zip"), key=lambda p: (p.parts[-3], int(re.search(r"\d+", p.stem).group())))
    if not archives:
        print("ОШИБКА: снимков нет. Запустите python tools/sync_examples.py")
        return 1
    failed = 0
    for archive in archives:
        project = archive.parts[-3]
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(tmp)
            (folder,) = Path(tmp).iterdir()
            results = check_flask(folder) if project.startswith("flask") else check_django(folder)
        bad = [(name, out) for code, out, name in results if code]
        failed += bool(bad)
        print(f"{'ОШИБКА' if bad else 'ok':6} {project} {archive.stem}: " + ", ".join(name for _, _, name in results))
        for name, out in bad:
            print(f"    {name}:\n" + "\n".join("      " + line for line in out.splitlines()[-15:]))
    print(f"Снимков: {len(archives)}, с ошибками: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
