"""Проверка страницы fastapi.html: шаги проходятся по порядку, а вывод совпадает с «Ожидаемым результатом».

Проект начинается с пустой папки fastapi-todo. Для каждого шага блоки main.py и test_main.py записываются
в папку, затем каждый <pre class="step-output" data-check="…"> сверяется с настоящим выводом:
  dev   — что печатает fastapi dev main.py до «Application startup complete.»
          (путь к папке и номера процессов не сравниваются);
  http  — запрос data-request к приложению этого шага: код data-code и тело ответа в том виде,
          как его показывает /docs (JSON с отступом 2). Запросы шага идут по порядку к одному приложению;
  pytest — вывод pytest -q (время не сравнивается).
В конце main.py и test_main.py сверяются с examples/fastapi-todo.
Код выхода 1 при расхождениях. Нужны fastapi[standard] и pytest из tools/requirements.txt.

    python tools/check_fastapi.py          # проверить
    python tools/check_fastapi.py --show   # напечатать настоящий вывод для каждого data-check
"""
import html
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "fastapi.html"
FINAL = ROOT / "examples" / "fastapi-todo"
FILES = ("main.py", "test_main.py")

# Запросы шага к одному экземпляру приложения; печатает JSON-список [код, тело как в /docs или null]
CLIENT = r'''
import json, sys
from fastapi.testclient import TestClient
import main
client = TestClient(main.app)
out = []
for method, path, body in json.loads(sys.argv[1]):
    response = client.request(method, path, json=body)
    text = json.dumps(response.json(), indent=2, ensure_ascii=False) if response.content else None
    out.append([response.status_code, text])
print(json.dumps(out, ensure_ascii=False))
'''


def env():
    # PYTHONUNBUFFERED: строки stdout и stderr идут в том же порядке, что в терминале
    return {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1",
            "NO_COLOR": "1", "TERM": "dumb", "COLUMNS": "100"}


def steps():
    page = PAGE.read_text(encoding="utf-8")
    start = page.index('data-progress-list="fastapi"')
    part = page[start:page.index("</ol>", start)]
    result = []
    for body in re.split(r'(?=<li class="project-step)', part)[1:]:
        number = int(re.search(r'data-step="(\d+)"', body).group(1))
        codes = [(label.strip(), html.unescape(code) + "\n") for label, code in
                 re.findall(r'<div class="code-head">\s*<span>([^<]+)</span>.*?<pre><code>(.*?)</code></pre>', body, flags=re.S)]
        outputs = [(dict((k, html.unescape(v)) for k, v in re.findall(r'\s([\w-]+)="([^"]*)"', attrs)), html.unescape(text))
                   for attrs, text in re.findall(r'<pre class="step-output"([^>]*)>(.*?)</pre>', body, flags=re.S)]
        result.append((number, codes, [(a, t) for a, t in outputs if "data-check" in a]))
    return result


def norm(text):
    lines = [line.rstrip() for line in text.strip("\n").splitlines()]
    lines = [re.sub(r"(Will watch for changes in these directories: ).*", r"\1[…]", line) for line in lines]
    lines = [re.sub(r"process \[\d+\]", "process [N]", line) for line in lines]
    lines = [re.sub(r" in [\d.]+s$", " in …s", line) for line in lines]
    # Пустые строки между блоками fastapi dev и длина отступов (зависит от ширины терминала) не сравниваются
    return [re.sub(r" {2,}", " ", line) for line in lines if line]


def free(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def dev_output(folder):
    """Запускает fastapi dev main.py и возвращает вывод до «Application startup complete.»."""
    if not free(8000):
        raise SystemExit("Порт 8000 занят: остановите сервер, чтобы проверить вывод fastapi dev")
    process = subprocess.Popen([sys.executable, "-m", "fastapi", "dev", "main.py"], cwd=folder, env=env(),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                               errors="replace", start_new_session=(os.name != "nt"))
    lines, deadline = [], time.time() + 60
    try:
        for line in process.stdout:
            lines.append(line.rstrip("\n"))
            if "Application startup complete." in line or time.time() > deadline:
                break
    finally:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)  # вместе с процессом перезагрузчика
        process.wait(timeout=30)
    return "\n".join(lines)


def main():
    show = "--show" in sys.argv
    errors = []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / "fastapi-todo"
        folder.mkdir()
        for number, codes, outputs in steps():
            for label, code in codes:
                if label in FILES:
                    (folder / label).write_text(code, encoding="utf-8", newline="\n")
            requests = []
            for attrs, _ in outputs:
                if attrs["data-check"] == "http":
                    method, path, *body = attrs["data-request"].split(" ", 2)
                    requests.append([method, path, json.loads(body[0]) if body else None])
            answers = []
            if requests:
                run = subprocess.run([sys.executable, "-c", CLIENT, json.dumps(requests, ensure_ascii=False)], cwd=folder,
                                     env=env(), capture_output=True, text=True, encoding="utf-8", errors="replace")
                if run.returncode:
                    errors.append(f"шаг {number}: запросы не выполнились:\n{run.stderr[-1500:]}")
                    continue
                answers = json.loads(run.stdout)
            for attrs, expected in outputs:
                key = attrs["data-check"]
                if key == "http":
                    code, body = answers.pop(0)
                    actual = body if body is not None else f"Code {code}"
                    label = f"{attrs['data-request']} -> {code}"
                    if str(code) != attrs["data-code"]:
                        errors.append(f"шаг {number} [{attrs['data-request']}]: код {code}, на странице {attrs['data-code']}")
                elif key == "dev":
                    actual, label = dev_output(folder), "fastapi dev"
                elif key == "pytest":
                    run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=folder, env=env(),
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
                    actual, label = run.stdout, "pytest -q"
                else:
                    errors.append(f"шаг {number}: неизвестная проверка data-check=\"{key}\"")
                    continue
                if show:
                    print(f"--- шаг {number} [{label}]\n{actual}")
                if norm(expected) != norm(actual):
                    errors.append(f"шаг {number} [{label}]: вывод расходится со страницей.\nНа странице:\n{expected}\nНа самом деле:\n{actual}")
        for name in FILES:
            mine = (folder / name).read_text(encoding="utf-8")
            if mine != (FINAL / name).read_text(encoding="utf-8").replace("\r\n", "\n"):
                errors.append(f"examples/fastapi-todo/{name} не совпадает с кодом после последнего шага")

    for error in errors:
        print("ОШИБКА", error, "\n")
    checked = sum(len(o) for _, _, o in steps())
    print(f"Шагов: {len(steps())}, проверено блоков «Ожидаемый результат»: {checked}, ошибок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
