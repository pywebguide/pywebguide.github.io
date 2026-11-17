"""Проверка страницы django-next.html: шаги проходятся по порядку, а вывод совпадает с «Ожидаемым результатом».

Начало — итоговый код первого проекта (examples/django-todo) с двумя задачами в базе, как у ученика.
Для каждого шага:
  * блоки кода с подписью-файлом (tasks/models.py, mysite/urls.py…) записываются в проект;
  * команды из блоков «Терминал» (makemigrations, migrate, check, test) выполняются;
  * блок «python manage.py shell» вводится строка за строкой, как в терминале (code.InteractiveConsole);
  * каждый <pre class="step-output" data-check="…"> сверяется с настоящим выводом:
      check, makemigrations, migrate, test — вывод команды (время теста не сравнивается);
      shell — стенограмма сессии;
      test-fail — строки FAIL/AssertionError, если убрать select_related;
      get:/путь, post-empty:/путь — фрагмент HTML-ответа (пробелы не важны).
Строка «…» в ожидаемом выводе заменяет любое число строк.
В конце миграция 0002 и файлы проекта сверяются с examples/django-next.
Код выхода 1 при расхождениях. Нужен Django из tools/requirements.txt.

    python tools/check_django_next.py          # проверить
    python tools/check_django_next.py --show   # напечатать настоящий вывод для каждого data-check
"""
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "django-next.html"
START = ROOT / "examples" / "django-todo"
FINAL = ROOT / "examples" / "django-next"
FILE_LABEL = re.compile(r"^(tasks|mysite)/[\w/]+\.(py|html)$")
SHELL_LABEL = "python manage.py shell"
STARTER_TASKS = ("Купить хлеб", "Прочитать главу")

# Ввод строк в shell так, как их видно в терминале: «>>> » и «... » перед строкой, затем результат.
# Пространство имён то же, что у python manage.py shell: модели импортированы автоматически.
CONSOLE = r'''
import code, sys
from django.core.management.commands.shell import Command
namespace = Command().get_namespace(verbosity=0)
console = code.InteractiveConsole(namespace)
sys.stderr = sys.stdout
more = False
for line in open(LINES, encoding="utf-8").read().splitlines():
    print(("... " if more else ">>> ") + line)
    more = console.push(line)
'''


class Project:
    def __init__(self, folder):
        self.dir = Path(folder)

    def run(self, *args, ok=True, black=False):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
        if not black:
            env["PATH"] = ""  # без black: makemigrations пишет файл так же, как у ученика без форматтера
        # stderr в тот же поток, что stdout: строки идут в том же порядке, что в терминале
        result = subprocess.run([sys.executable, "manage.py", *args], cwd=self.dir, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env, timeout=300)
        out = result.stdout.rstrip()
        if ok and result.returncode:
            raise RuntimeError(f"manage.py {' '.join(args)}:\n{out[-2000:]}")
        return out

    def write(self, rel, text):
        path = self.dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def shell(self, lines):
        script = self.dir / "_lines.txt"
        script.write_text(lines, encoding="utf-8")
        out = self.run("shell", "-v", "0", "-c", CONSOLE.replace("LINES", repr(str(script))))
        script.unlink()
        return out

    def request(self, method, path, data=None):
        probe = ("from django.test import Client\nfrom django.test.utils import setup_test_environment\n"
                 "setup_test_environment()\nimport sys\n"
                 f"response = Client().{method}({path!r}, {data!r})\n"
                 "sys.stdout.write(response.content.decode())")
        return self.run("shell", "-v", "0", "-c", probe)


def steps():
    """[(номер, [(подпись, код)], [(ключ, ожидаемый текст)])] из списка шагов страницы."""
    page = PAGE.read_text(encoding="utf-8")
    start = page.index('data-progress-list="django-next"')
    part = page[start:page.index("</ol>", start)]
    result = []
    # Шаг — от <li class="project-step"> до следующего такого же: внутри шага бывают свои списки <li>
    for body in re.split(r'(?=<li class="project-step)', part)[1:]:
        number = int(re.search(r'data-step="(\d+)"', body).group(1))
        codes = [(label.strip(), html.unescape(code) + "\n") for label, code in
                 re.findall(r'<div class="code-head">\s*<span>([^<]+)</span>.*?<pre><code>(.*?)</code></pre>', body, flags=re.S)]
        outputs = [(key, html.unescape(text)) for key, text in
                   re.findall(r'<pre class="step-output" data-check="([^"]+)">(.*?)</pre>', body, flags=re.S)]
        result.append((number, codes, outputs))
    return result


def norm_lines(text):
    lines = [line.rstrip() for line in text.strip("\n").splitlines()]
    return [re.sub(r"Ran (\d+) tests? in [\d.]+s", r"Ran \1 tests in …s", line) for line in lines]


def matches(expected, actual):
    """Построчное сравнение; строка «…» в ожидаемом выводе заменяет любое число строк."""
    exp, act = norm_lines(expected), norm_lines(actual)

    def go(i, j):
        if i == len(exp):
            return j == len(act)
        if exp[i] == "…":
            return any(go(i + 1, k) for k in range(j, len(act) + 1))
        return j < len(act) and exp[i] == act[j] and go(i + 1, j + 1)
    return go(0, 0)


def squeeze(text):
    return re.sub(r"\s+", " ", text).strip()


def main():
    show = "--show" in sys.argv
    errors = []
    with tempfile.TemporaryDirectory() as tmp:
        project = Project(Path(tmp) / "site")
        shutil.copytree(START, project.dir, ignore=shutil.ignore_patterns("steps", "__pycache__", "*.sqlite3", "README.txt"))
        project.run("migrate", "-v", "0")
        project.shell("".join(f"Task.objects.create(title={t!r})\n" for t in STARTER_TASKS))

        for number, codes, outputs in steps():
            got = {}
            for label, code in codes:
                if FILE_LABEL.match(label):
                    project.write(label, code)
            for label, code in codes:
                if label == "Терминал":
                    for command in code.splitlines():
                        args = command.split()[2:] if command.startswith("python manage.py") else None
                        if args and args[0] in ("makemigrations", "migrate", "check", "test"):
                            got[args[0]] = project.run(*args, ok=args[0] != "test")
                elif label == SHELL_LABEL:
                    got["shell"] = project.shell(code)
            for key, expected in outputs:
                if key in got:
                    actual = got[key]
                elif key == "check":
                    actual = project.run("check")
                elif key == "test-fail":
                    views = project.dir / "tasks" / "views.py"
                    original = views.read_text(encoding="utf-8")
                    views.write_text(original.replace('select_related("category")', "all()"), encoding="utf-8")
                    out = project.run("test", ok=False)
                    views.write_text(original, encoding="utf-8")
                    actual = "\n".join(l for l in out.splitlines() if l.startswith(("FAIL:", "AssertionError", "FAILED")))
                elif key.startswith(("get:", "post-empty:")):
                    kind, path = key.split(":", 1)
                    body = project.request("get", path) if kind == "get" else project.request("post", path, {"title": ""})
                    ok = squeeze(expected) in squeeze(body)
                    if show:
                        print(f"--- шаг {number} [{key}] фрагмент {'найден' if ok else 'НЕ найден'}")
                    if not ok:
                        errors.append(f"шаг {number} [{key}]: фрагмента нет в ответе:\n{expected}\n--- ответ:\n{body[:3000]}")
                    continue
                else:
                    errors.append(f"шаг {number}: неизвестная проверка data-check=\"{key}\" или команда не выполнялась в этом шаге")
                    continue
                if show:
                    print(f"--- шаг {number} [{key}]\n{actual}")
                if not matches(expected, actual):
                    errors.append(f"шаг {number} [{key}]: вывод расходится со страницей.\nНа странице:\n{expected}\nНа самом деле:\n{actual}")

        # Миграция, созданная по шагам, и итоговые файлы совпадают с examples/django-next
        made = sorted((project.dir / "tasks" / "migrations").glob("0002_*.py"))
        stored = sorted((FINAL / "tasks" / "migrations").glob("0002_*.py"))
        drop_date = lambda p: p.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n", 1)[1]
        if [p.name for p in made] != [p.name for p in stored] or (made and drop_date(made[0]) != drop_date(stored[0])):
            errors.append(f"миграция 0002 отличается от examples/django-next: {[p.name for p in made]} / {[p.name for p in stored]}")
        for path in sorted(FINAL.rglob("*")):
            rel = path.relative_to(FINAL)
            if path.is_file() and rel.suffix in (".py", ".html") and "__pycache__" not in rel.parts and "migrations" not in rel.parts:
                mine = project.dir / rel
                if not mine.exists() or mine.read_text(encoding="utf-8") != path.read_text(encoding="utf-8").replace("\r\n", "\n"):
                    errors.append(f"examples/django-next/{rel.as_posix()} не совпадает с кодом после последнего шага")

    for error in errors:
        print("ОШИБКА", error, "\n")
    checked = sum(len(o) for _, _, o in steps())
    print(f"Шагов: {len(steps())}, проверено блоков «Ожидаемый результат»: {checked}, ошибок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
