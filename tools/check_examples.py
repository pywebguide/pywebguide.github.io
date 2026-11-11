"""Проверка примеров кода: блоки data-run запускаются, остальные блоки *.py проверяются на синтаксис."""
import ast
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from codeblocks import read

ROOT = Path(__file__).resolve().parent.parent
NOT_PYTHON = ("Терминал", ".html", "SQL", "JSON", ".gitignore", "requirements", "JavaScript", ".js", "HTTP", ".md")


def main():
    failed = checked = ran = 0
    for path in sorted(ROOT.glob("*.html")):
        for block in read(path):
            label = block["label"].strip()
            if block["run"]:
                ran += 1
                with tempfile.TemporaryDirectory() as folder:
                    result = subprocess.run([sys.executable, "-c", block["code"]], cwd=folder, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
                if result.returncode:
                    failed += 1
                    print(f"ОШИБКА запуска {path.name} «{label}»:\n{result.stderr[-600:]}")
            elif label.endswith(".py") or "WSGI" in label or not any(mark in label for mark in NOT_PYTHON):
                checked += 1
                try:
                    ast.parse(textwrap.dedent(block["code"]))
                except SyntaxError as error:
                    failed += 1
                    print(f"ОШИБКА синтаксиса {path.name} «{label}»: {error}")
    print(f"Запущено: {ran}, проверено на синтаксис: {checked}, ошибок: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
