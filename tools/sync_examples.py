"""Полный код первого проекта лежит в examples/ и совпадает с кодом на странице project.html.

Источник правды — страница: из её блоков кода берутся финальные версии файлов
(Flask: шаг 5, Django: шаги 3, 7, 8, 9). Файлы, которых на странице нет (settings.py,
миграции, тесты), созданы командами django-admin/makemigrations и лежат в examples/ как есть.

Кроме итогового кода собираются снимки examples/<проект>/steps/step-N/ — состояние проекта
после шага N — и архивы step-N.zip рядом. Снимок есть только у шагов, которые меняют файлы:
блоки кода с подписью-файлом и команды startproject/startapp (скелет проекта) и makemigrations
(миграция из examples/). Скелет Django создаёт настоящий django-admin без форматтеров, поэтому
нужен Django из tools/requirements.txt. Ссылки «Код после этого шага (.zip)» на странице
проставляются сами и тоже проверяются.

Так же код раздела «Django дальше» (django-next.html) лежит в examples/django-next: файлы из блоков
кода страницы (последний блок с подписью-файлом в списке шагов), миграция 0002 — от makemigrations.
Что шаги страницы проходятся по порядку, проверяет tools/check_django_next.py.
Код раздела «Первое API на FastAPI» (fastapi.html) — examples/fastapi-todo, его проверяет tools/check_fastapi.py.

    python tools/sync_examples.py           # обновить examples/, снимки, архивы и ссылки на странице
    python tools/sync_examples.py --check   # только проверить совпадение (для CI)
"""
import html
import io
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"
PAGE = ROOT / "project.html"
SKIP_PARTS = {"__pycache__", "steps", ".pytest_cache"}

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
PROJECTS = {"flask-todo": ("flask", "Список задач на Flask", FLASK), "django-todo": ("django", "Список задач на Django", DJANGO)}
SETTINGS = "mysite/settings.py"
MIGRATION = "tasks/migrations/0001_initial.py"
LINK_TEXT = "Код после этого шага (.zip)"
LINK_RE = re.compile(r'[ \t]*<p class="download-row step-download">.*?</p>\n')

BLOCK_RE = r'<div class="code-head">\s*<span>([^<]+)</span>.*?<pre><code>(.*?)</code></pre>'


def blocks(section_html):
    found = {}
    for label, code in re.findall(BLOCK_RE, section_html, flags=re.S):
        found[label] = html.unescape(code) + "\n"
    return found


def section(page, name):
    ends = {"flask": ('id="flask"', 'id="django"'), "django": ('id="django"', 'id="errors"')}[name]
    return page.index(ends[0]), page.index(ends[1])


# Страница «Django дальше»: подпись блока совпадает с путём файла в examples/django-next
NEXT_PAGE = ROOT / "django-next.html"
NEXT_FILES = ["tasks/models.py", "tasks/admin.py", "tasks/forms.py", "tasks/views.py", "mysite/urls.py",
              "tasks/templates/tasks/index.html", "tasks/templates/tasks/task_form.html", "tasks/tests.py"]
# Страница «Первое API на FastAPI»: main.py и test_main.py в examples/fastapi-todo
FASTAPI_PAGE = ROOT / "fastapi.html"
FASTAPI_FILES = ["main.py", "test_main.py"]
ARCHIVES = [*PROJECTS, "django-next", "fastapi-todo"]


def expected():
    page = PAGE.read_text(encoding="utf-8")
    files = {}
    for project, (name, _, mapping) in PROJECTS.items():
        start, end = section(page, name)
        found = blocks(page[start:end])
        for label, target in mapping.items():
            files[f"{project}/{target}"] = found[label]
    page = NEXT_PAGE.read_text(encoding="utf-8")
    start = page.index('data-progress-list="django-next"')
    found = blocks(page[start:page.index("</ol>", start)])
    for rel in NEXT_FILES:
        files[f"django-next/{rel}"] = found[rel]
    page = FASTAPI_PAGE.read_text(encoding="utf-8")
    start = page.index('data-progress-list="fastapi"')
    found = blocks(page[start:page.index("</ol>", start)])
    for rel in FASTAPI_FILES:
        files[f"fastapi-todo/{rel}"] = found[rel]
    return files


# ---------- снимки по шагам ----------

def steps(page, name):
    """Шаги раздела: [(номер, начало <li>, конец </li>, [(подпись, код), ...])]."""
    start, end = section(page, name)
    result = []
    # Шаг — от <li class="project-step"> до его метки «Шаг пройден»: внутри шага бывают свои списки <li>
    for m in re.finditer(r'<li class="project-step[^"]*">.*?<label class="step-check">.*?</label>\n\s*</li>\n', page[start:end], flags=re.S):
        body = m.group(0)
        number = int(re.search(r'data-step="(\d+)"', body).group(1))
        codes = [(label.strip(), html.unescape(code) + "\n") for label, code in re.findall(BLOCK_RE, body, flags=re.S)]
        result.append((number, start + m.start(), start + m.end(), codes))
    return result


_skeleton = None


def django_skeleton():
    """Файлы, которые создают django-admin startproject mysite . и manage.py startapp tasks.

    PATH пустой: так Django не находит black и не переформатирует файлы, результат одинаков везде.
    settings.py (в нём случайный SECRET_KEY) и миграция берутся из examples/django-todo — как в итоговом коде.
    """
    global _skeleton
    if _skeleton is None:
        with tempfile.TemporaryDirectory() as folder:
            env = {**os.environ, "PATH": ""}
            for args in (["-m", "django", "startproject", "mysite", "."], ["manage.py", "startapp", "tasks"]):
                subprocess.run([sys.executable, *args], cwd=folder, env=env, check=True, capture_output=True)
            base = Path(folder)
            _skeleton = {p.relative_to(base).as_posix(): p.read_text(encoding="utf-8")
                         for p in sorted(base.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
        final_settings = (EX / "django-todo" / SETTINGS).read_text(encoding="utf-8")
        # До шага 2 приложение tasks ещё не подключено
        _skeleton[SETTINGS] = final_settings.replace("    'tasks',\n", "", 1)
    return dict(_skeleton)


def apply_installed_apps(settings, block):
    return re.sub(r"INSTALLED_APPS = \[.*?\]\n", lambda m: block, settings, count=1, flags=re.S)


def snapshots():
    """{(проект, номер шага): {путь: текст}} — только для шагов, которые меняют файлы."""
    page = PAGE.read_text(encoding="utf-8")
    result = {}
    for project, (name, title, mapping) in PROJECTS.items():
        state = {}
        all_steps = steps(page, name)
        for number, _, _, codes in all_steps:
            before = dict(state)
            for label, code in codes:
                if label == "Терминал":
                    if "startproject" in code:
                        state.update(django_skeleton())
                    if "makemigrations" in code:
                        state[MIGRATION] = (EX / project / MIGRATION).read_text(encoding="utf-8")
                elif label == SETTINGS:
                    state[SETTINGS] = apply_installed_apps(state[SETTINGS], code)
                elif label in mapping:
                    state[mapping[label]] = code
            if state != before:
                files = dict(state)
                files["requirements.txt"] = (EX / project / "requirements.txt").read_text(encoding="utf-8")
                files["README.txt"] = readme(project, name, title, number, len(all_steps))
                result[(project, number)] = files
        # Последний снимок и итоговый код в examples/ должны совпадать (кроме тестов и README)
        final = EX / project
        for rel, text in state.items():
            if rel.endswith("tests.py"):
                continue
            current = (final / rel).read_text(encoding="utf-8").replace("\r\n", "\n") if (final / rel).exists() else None
            if current != text:
                raise SystemExit(f"Снимок последнего шага {project} расходится с examples/{project}/{rel}")
    return result


def readme(project, name, title, number, total):
    run = ("flask --app app run --debug" if name == "flask" else "python manage.py runserver")
    done = "шаг 1 сделан" if number == 1 else f"шаги 1–{number} сделаны"
    return (
        f"{title} — код после шага {number} из {total} (PyWeb Guide)\n"
        f"https://pywebguide.github.io/project.html#{name}\n\n"
        f"Так выглядит проект, если {done} правильно. Сверьте с ним свои файлы\n"
        f"или распакуйте и продолжайте с шага {number + 1}.\n"
        f"Полный код проекта: https://pywebguide.github.io/examples/{project}.zip\n\n"
        "Окружение и зависимости — как в шаге 1:\n"
        "    python -m venv .venv\n"
        "    .venv\\Scripts\\activate          (macOS и Linux: source .venv/bin/activate)\n"
        "    pip install -r requirements.txt\n"
        f"Запуск: {run}\n"
    )


# ---------- архивы ----------

def pack_files(prefix, files):
    """Zip из {путь: байты}. Фиксированная дата: архив не меняется, если не менялись файлы.

    Порядок без учёта регистра и create_system=0 — как у архивов, собранных на Windows:
    архив выходит одинаковым байт в байт на любой системе.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in sorted(files, key=str.lower):
            info = zipfile.ZipInfo(f"{prefix}/{rel}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0
            zf.writestr(info, files[rel].replace(b"\r\n", b"\n"))
    return buffer.getvalue()


def folder_files(folder):
    return {path.relative_to(folder).as_posix(): path.read_bytes() for path in sorted(folder.rglob("*"))
            if path.is_file() and not (set(path.relative_to(folder).parts) & SKIP_PARTS)
            and path.suffix not in (".sqlite3", ".db", ".pyc", ".zip")}


# ---------- ссылки на странице ----------

def link_html(project, number, indent):
    return (f'{indent}<p class="download-row step-download"><a href="examples/{project}/steps/step-{number}.zip" download>'
            f'{LINK_TEXT}</a></p>\n')


def page_with_links(page, snaps):
    page = LINK_RE.sub("", page)
    inserts = []
    for project, (name, _, _) in PROJECTS.items():
        for number, start, end, _ in steps(page, name):
            if (project, number) not in snaps:
                continue
            body = page[start:end]
            anchor = re.search(r'\n([ \t]*)<div class="step-result">', body) or re.search(r'\n([ \t]*)<label class="step-check">', body)
            inserts.append((start + anchor.start() + 1, link_html(project, number, anchor.group(1))))
    for pos, text in sorted(inserts, reverse=True):
        page = page[:pos] + text + page[pos:]
    return page


# ---------- сверка и запись ----------

def wanted():
    """Все файлы, которые должна дать сборка ({путь от examples/: байты}), и снимки по шагам."""
    files = {rel: text.encode("utf-8") for rel, text in expected().items()}
    snaps = snapshots()
    for (project, number), snap in snaps.items():
        base = f"{project}/steps/step-{number}"
        data = {rel: text.encode("utf-8") for rel, text in snap.items()}
        for rel, content in data.items():
            files[f"{base}/{rel}"] = content
        files[f"{base}.zip"] = pack_files(f"{project}-step-{number}", data)
    return files, snaps


def main():
    check = "--check" in sys.argv
    files, snaps = wanted()
    stale = []
    for rel, content in files.items():
        path = EX / rel
        if rel.endswith(".zip"):
            same = path.exists() and path.read_bytes() == content
        else:
            same = path.exists() and path.read_bytes().replace(b"\r\n", b"\n") == content
        if not same:
            stale.append(rel)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
    # Лишние файлы в steps/ (снимок шага, который больше ничего не меняет)
    for project in PROJECTS:
        for path in sorted((EX / project / "steps").rglob("*")) if (EX / project / "steps").exists() else []:
            rel = path.relative_to(EX).as_posix()
            if path.is_file() and rel not in files and "__pycache__" not in path.parts:
                stale.append(rel + " (лишний)")
                if not check:
                    path.unlink()
    page = PAGE.read_text(encoding="utf-8")
    new_page = page_with_links(page, snaps)
    if new_page != page:
        stale.append("project.html: ссылки «Код после этого шага»")
        if not check:
            PAGE.write_text(new_page, encoding="utf-8", newline="\n")
    # Итоговые архивы
    for project in ARCHIVES:
        archive = EX / f"{project}.zip"
        data = pack_files(project, folder_files(EX / project))
        if not archive.exists() or archive.read_bytes() != data:
            stale.append(f"{project}.zip")
            if not check:
                archive.write_bytes(data)
    if check:
        if stale:
            print("Код в examples/ отличается от project.html. Запустите python tools/sync_examples.py:")
            shown = sorted({re.sub(r"(/steps/step-\d+)/.*", r"\1/", s) for s in stale})
            print("\n".join("  " + s for s in shown))
            sys.exit(1)
        print(f"examples/ совпадает с project.html, снимков шагов: {len(snaps)}")
        return
    for project in PROJECTS:
        steps_dir = EX / project / "steps"
        for folder in sorted(steps_dir.rglob("*"), reverse=True) if steps_dir.exists() else []:
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
    print(f"Обновлено: {len(stale)}, снимков шагов: {len(snaps)}: " + ", ".join(f"{p} {n}" for p, n in snaps))


if __name__ == "__main__":
    main()
