Список задач на Django с категориями — код раздела «Django дальше» PyWeb Guide (шаги 1–9)
https://pywebguide.github.io/django-next.html

Продолжение первого проекта (examples/django-todo): модель Category и ForeignKey,
select_related, представления на классах ListView и CreateView, тесты.
Проверено: Python 3.13, Django 6.1.

Windows (PowerShell):
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver

macOS и Linux: то же самое, но python3 вместо python при создании окружения
и source .venv/bin/activate для его включения.

Откройте http://127.0.0.1:8000/ (список) и http://127.0.0.1:8000/admin/ (админка,
там же добавляются категории).
Проверка: python manage.py test

Важно: SECRET_KEY в mysite/settings.py создан командой django-admin и подходит
только для учёбы на своём компьютере. Перед публикацией замените его и выключите DEBUG
(см. раздел «Публикация»).
