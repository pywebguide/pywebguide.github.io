Список задач на FastAPI — код раздела «Первое API на FastAPI» PyWeb Guide (шаги 1–6)
https://pywebguide.github.io/fastapi.html

REST API: GET /tasks, POST /tasks, GET /tasks/{task_id}, DELETE /tasks/{task_id}.
Задачи хранятся в памяти и пропадают при перезапуске сервера.
Проверено: Python 3.13, FastAPI 0.163, Pydantic 2.14.

Windows (PowerShell):
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    fastapi dev main.py

macOS и Linux: то же самое, но python3 вместо python при создании окружения
и source .venv/bin/activate для его включения.

Откройте http://127.0.0.1:8000/docs — там можно отправить любой запрос кнопкой Try it out.
Проверка: pytest -q
