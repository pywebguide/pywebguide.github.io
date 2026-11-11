"""Объяснения ошибок (ERROR_HINTS в features.js) срабатывают на настоящих сообщениях Python, Flask и SQLite.

Каждый пример ниже падает с ошибкой. Для её текста функция explainError из features.js должна
вернуть объяснение, а у каждого объяснения должен быть перевод на казахский и английский
в assets/i18n.js. Нужны Node.js и Flask. Код выхода 1 при ошибках.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FLASK = "from flask import Flask, render_template, render_template_string, request, url_for\napp = Flask(__name__)\n"
INSIDE = FLASK + "with app.test_request_context(method='POST'):\n    "
SQL = "import sqlite3\ndb = sqlite3.connect(':memory:')\ndb.execute('CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL)')\n"

CASES = [
    # Python
    "if x > 5\n    pass", "print((1, 2)", 'x = "abc', 'print "hi"', "if x = 5:\n    pass", "a = [1 2]", "x = = 1",
    "if True:\npass", "x = 1\n    y = 2", "print(nmae)", "def f():\n    n += 1\nf()", '"a" + 1', '1 + "a"',
    "def g(a): pass\ng()", "def g(a): pass\ng(1, 2)", "x = 5\nx()", "x = None\nx[0]", "for i in None: pass", "x = 5\nx[0]",
    "len(5)", 'int("abc")', "a, b = [1]", "import math\nmath.sqrt(-1)", "[1][3]", '{"a": 1}["name"]', "None.strip()",
    '"a".push(1)', "1 / 0", "import flsk", "from math import Sqrt", "def r(): r()\nr()", 'open("nofile.txt")',
    'import json\njson.loads("{\'a\': 1}")',
    # Flask и шаблоны
    INSIDE + "render_template('nope.html')",
    INSIDE + "render_template_string('{{ user.name }}')",
    INSIDE + "render_template_string('{% for a in b %}')",
    INSIDE + "url_for('nope')",
    INSIDE + "request.form['title']",
    FLASK + "url_for('index')",
    FLASK + "@app.get('/a')\ndef page(): return ''\n@app.get('/b')\ndef page(): return ''",
    # SQLite
    SQL + "db.execute('SELECT * FROM users')",
    SQL + "db.execute('SELECT name FROM tasks')",
    SQL + "db.execute('SELEC * FROM tasks')",
    SQL + "db.execute('INSERT INTO tasks (title) VALUES (NULL)')",
    SQL + "db.execute('INSERT INTO tasks (title) VALUES (?)', ('a', 'b'))",
]

NODE = r"""
const fs = require("fs");
const [features, i18n, casesPath] = process.argv.slice(2);
const src = fs.readFileSync(features, "utf8");
const a = src.indexOf("  const ERROR_HINTS = ["), b = src.indexOf("  // Событие для воронки GoatCounter");
if (a === -1 || b === -1) throw new Error("в features.js не найдена таблица ERROR_HINTS");
const plain = (text, vars) => text.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
const used = [];
const explain = new Function("t", src.slice(a, b) + "\nreturn { explainError: explainError, hints: ERROR_HINTS };")(
  (text, vars) => { used.push(text); return plain(text, vars); });
const answers = JSON.parse(fs.readFileSync(casesPath, "utf8")).map((error) => explain.explainError(error));
const strings = Array.from(new Set(explain.hints.map((row) => row[1]).concat(used)));
const missing = [];
for (const lang of ["kk", "en"]) {
  const win = {};
  new Function("window", "document", fs.readFileSync(i18n, "utf8"))(win, { documentElement: { lang: lang } });
  for (const text of strings) if (win.pywebT(text) === text) missing.push(lang + ": " + text);
}
console.log(JSON.stringify({ answers: answers, missing: missing, hints: explain.hints.length }));
"""


def error_of(code):
    try:
        exec(compile(code, "<exec>", "exec"), {"__name__": "__main__"})
    except BaseException:  # нужна любая ошибка, включая SyntaxError и RecursionError
        return traceback.format_exc()
    return ""


def main():
    node = shutil.which("node")
    if not node:
        print("ОШИБКА: не найден Node.js, он нужен, чтобы выполнить explainError из features.js")
        return 1
    errors = [error_of(code) for code in CASES]
    with tempfile.TemporaryDirectory() as folder:
        cases = Path(folder) / "cases.json"
        script = Path(folder) / "explain.js"
        cases.write_text(json.dumps(errors, ensure_ascii=False), encoding="utf-8")
        script.write_text(NODE, encoding="utf-8")
        result = subprocess.run([node, str(script), str(ROOT / "features.js"), str(ROOT / "assets" / "i18n.js"), str(cases)],
                                capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        print("ОШИБКА запуска Node.js:\n" + result.stderr[-1500:])
        return 1
    report = json.loads(result.stdout)
    failed = 0
    for code, error, answer in zip(CASES, errors, report["answers"]):
        last = error.strip().splitlines()[-1] if error else "код не упал"
        if not error or not answer:
            failed += 1
            print(f"ОШИБКА: нет объяснения для «{last}»\n  код: {code.splitlines()[-1]}")
    for line in report["missing"]:
        failed += 1
        print("ОШИБКА: нет перевода в assets/i18n.js —", line)
    print(f"Объяснений в таблице: {report['hints']}, проверено ошибок: {len(CASES)}, проблем: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
