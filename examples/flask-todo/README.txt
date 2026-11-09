Список задач на Flask — полный код первого проекта PyWeb Guide (шаги 1–6)
https://pywebguide.github.io/project.html#flask

Проверено: Python 3.13, Flask 3.1.

Windows (PowerShell):
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    flask --app app run --debug

macOS и Linux:
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    flask --app app run --debug

Откройте http://127.0.0.1:5000/. Задачи хранятся в файле tasks.db рядом с app.py.
Проверка: python -m unittest test_app
