"""Эталонные решения задач проходят свои скрытые тесты, а стартовый код — нет.

Для каждой <article class="task"> в practice.html (и в переводах kk/, en/):
  - решение из «Показать решение» + тесты из <template data-kind="tests"> должны пройти;
  - стартовый код из <textarea> + те же тесты должны упасть (иначе задача решается ничем).
Тесты запускаются тем же способом, что и в браузере: функция check() из assets/checker.py.
Код выхода 1 при ошибках.
"""
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKER = (ROOT / "assets" / "checker.py").read_text(encoding="utf-8")


class Tasks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tasks = []
        self.task = None
        self.field = None
        self.in_solution = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "task" in (attrs.get("class") or "").split():
            self.task = {"id": attrs.get("data-task"), "starter": "", "solution": "", "tests": ""}
        if self.task is None:
            return
        if tag == "textarea":
            self.field = "starter"
        if tag == "details" and "solution" in (attrs.get("class") or "").split():
            self.in_solution = True
        if tag == "code" and self.in_solution:
            self.field = "solution"
        if tag == "template" and attrs.get("data-kind") == "tests":
            self.field = "tests"

    def handle_endtag(self, tag):
        if tag in ("textarea", "code", "template"):
            self.field = None
        if tag == "details":
            self.in_solution = False
        if tag == "article" and self.task is not None:
            self.tasks.append(self.task)
            self.task = None

    def handle_data(self, data):
        if self.task is not None and self.field:
            self.task[self.field] += data


def run(code, tests):
    script = CHECKER + "\n" + f"check({code!r}, {tests!r})\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(script)
    try:
        return subprocess.run([sys.executable, "-I", "-X", "utf8", f.name], capture_output=True, text=True, encoding="utf-8", timeout=60, cwd=tempfile.gettempdir())
    finally:
        Path(f.name).unlink()


def main():
    errors = []
    total = 0
    for page in [ROOT / "practice.html", ROOT / "kk" / "practice.html", ROOT / "en" / "practice.html"]:
        if not page.exists():
            continue
        parser = Tasks()
        parser.feed(page.read_text(encoding="utf-8"))
        name = page.relative_to(ROOT).as_posix()
        for task in parser.tasks:
            total += 1
            if not task["solution"].strip() or not task["tests"].strip():
                errors.append(f"{name} {task['id']}: нет решения или тестов")
                continue
            good = run(task["solution"], task["tests"])
            if good.returncode != 0:
                errors.append(f"{name} {task['id']}: решение не проходит тесты\n{good.stdout}{good.stderr}")
            bad = run(task["starter"], task["tests"])
            if bad.returncode == 0:
                errors.append(f"{name} {task['id']}: стартовый код проходит тесты, задача решается без кода")
    for error in errors:
        print(error)
    print(f"Задач: {total}, ошибок: {len(errors)}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
