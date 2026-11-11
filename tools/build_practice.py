"""Собирает задачи на странице practice.html (и переводах kk/, en/) из описания ниже.

Задачи вписываются между метками <!-- tasks:start --> и <!-- tasks:end -->.
Текст может быть строкой (общей для всех языков) или словарем {"ru": ..., "kk": ..., "en": ...};
если перевода нет, берётся русский. Тесты пишутся через case(выражение, ожидаемое, подсказка),
см. assets/checker.py. После правки:

    python tools/build_practice.py            # переписать страницы
    python tools/build_practice.py --check    # только проверить (для CI)
    python tools/check_tasks.py      # решения проходят тесты, стартовый код — нет
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LEVELS = {
    "easy": {"ru": "Лёгкая", "kk": "Жеңіл", "en": "Easy"},
    "medium": {"ru": "Средняя", "kk": "Орташа", "en": "Medium"},
    "hard": {"ru": "Сложная", "kk": "Күрделі", "en": "Hard"},
}

UI = {
    "check": {"ru": "Проверить", "kk": "Тексеру", "en": "Check"},
    "reset": {"ru": "Сбросить", "kk": "Тастау", "en": "Reset"},
    "solution": {"ru": "Показать решение", "kk": "Шешімін көрсету", "en": "Show solution"},
    "hint": {"ru": "Подсказка", "kk": "Кеңес", "en": "Hint"},
    "hints": {"ru": "Подсказки", "kk": "Кеңестер", "en": "Hints"},
    "answer": {"ru": "Решение", "kk": "Шешім", "en": "Solution"},
    "level": {"ru": "Уровень", "kk": "Деңгейі", "en": "Level"},
}

SECTIONS = [
    {
        "id": "basics",
        "title": {"ru": "Основы Python", "kk": "Python негіздері", "en": "Python basics"},
        "lead": {"ru": "Функции, строки и словари: на них держится любой обработчик запросов.",
                 "kk": "Функциялар, жолдар және сөздіктер: кез келген сұрау өңдегіші осыларға сүйенеді.",
                 "en": "Functions, strings and dictionaries: every request handler is built on them."},
        "tasks": ["greet", "words", "strong", "slug", "total", "evens", "truncate", "longest", "unique", "initials"],
    },
    {
        "id": "http",
        "title": {"ru": "HTTP и маршруты", "kk": "HTTP және маршруттар", "en": "HTTP and routes"},
        "lead": {"ru": "То, что фреймворк делает за вас, легко написать в простом виде.",
                 "kk": "Фреймворк сіз үшін істейтін нәрсені қарапайым түрде жазу оңай.",
                 "en": "What a framework does for you is easy to write in a simple form."},
        "tasks": ["query", "router", "validate", "json", "render", "paginate", "status", "mime", "build_url", "cookie", "redirect"],
    },
    {
        "id": "forms",
        "title": {"ru": "Формы и проверка данных", "kk": "Формалар және деректерді тексеру", "en": "Forms and data checks"},
        "lead": {"ru": "Всё, что прислал пользователь, сервер проверяет сам.", "kk": "Пайдаланушы жіберген нәрсенің бәрін сервер өзі тексереді.", "en": "The server checks everything a user sends on its own."},
        "tasks": ["clean", "to_int", "missing", "escape", "email"],
    },
    {
        "id": "sql",
        "title": {"ru": "SQL", "kk": "SQL", "en": "SQL"},
        "lead": {"ru": "Настоящая база SQLite работает прямо в браузере.",
                 "kk": "Нағыз SQLite дерекқоры тікелей браузерде жұмыс істейді.",
                 "en": "A real SQLite database runs right in the browser."},
        "tasks": ["add_task", "select", "count", "delete_done", "mark_done", "search"],
    },
    {
        "id": "flask",
        "title": {"ru": "Flask", "kk": "Flask", "en": "Flask"},
        "lead": {"ru": "Настоящий Flask. Первая проверка дополнительно загрузит пакет с PyPI.",
                 "kk": "Нағыз Flask. Алғашқы тексеру PyPI-дан пакетті қосымша жүктейді.",
                 "en": "Real Flask. The first check also downloads the package from PyPI."},
        "tasks": ["route", "filter", "post", "detail", "health", "square", "search_q", "remove"],
    },
]

TASKS = {
    "greet": {
        "level": "easy",
        "title": {"ru": "Приветствие"},
        "text": {"ru": "Напишите функцию <code>greet(name)</code>, которая возвращает строку <code>Привет, Имя!</code>. Лишние пробелы вокруг имени нужно убрать. Если имя пустое, верните <code>Привет, гость!</code>."},
        "starter": "def greet(name):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Склеить текст с переменной проще всего f-строкой: <code>f\"Привет, {name}!\"</code>.",
            "Пробелы по краям убирает <code>name.strip()</code>.",
            "Пустая строка в условии считается ложью: <code>name or 'гость'</code> вернёт «гость», если имя пустое.",
        ]},
        "solution": "def greet(name):\n    name = name.strip()\n    return f\"Привет, {name or 'гость'}!\"",
        "tests": "case('greet(\"Анна\")', \"Привет, Анна!\")\n"
                 "case('greet(\"  Ерлан \")', \"Привет, Ерлан!\", \"Уберите пробелы вокруг имени: подойдёт .strip()\")\n"
                 "case('greet(\"\")', \"Привет, гость!\", \"Для пустого имени нужен ответ «Привет, гость!»\")\n"
                 "case('greet(\"   \")', \"Привет, гость!\", \"Имя из одних пробелов тоже считается пустым\")",
    },
    "words": {
        "level": "easy",
        "title": {"ru": "Подсчёт слов"},
        "text": {"ru": "Напишите <code>count_words(text)</code>: верните словарь, где ключ — слово в нижнем регистре, а значение — сколько раз оно встретилось."},
        "starter": "def count_words(text):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Начните с пустого словаря <code>counts = {}</code> и пройдите циклом по словам.",
            "<code>text.lower().split()</code> переводит текст в нижний регистр и делит его по любым пробелам и переносам строк.",
            "<code>counts.get(word, 0) + 1</code> увеличивает счётчик, даже если слова ещё нет в словаре.",
        ]},
        "solution": "def count_words(text):\n    counts = {}\n    for word in text.lower().split():\n        counts[word] = counts.get(word, 0) + 1\n    return counts",
        "tests": "case('count_words(\"\")', {}, \"Для пустой строки нужен пустой словарь\")\n"
                 "case('count_words(\"Да да нет\")', {\"да\": 2, \"нет\": 1}, \"Приведите слова к нижнему регистру\")\n"
                 "case('count_words(\"a  b\\\\nb\")', {\"a\": 1, \"b\": 2}, \"Разделяйте через .split() без аргументов\")",
    },
    "strong": {
        "level": "easy",
        "title": {"ru": "Надёжный пароль"},
        "text": {"ru": "Напишите <code>is_strong(password)</code>. Пароль надёжный, если в нём не меньше 8 символов, есть хотя бы одна цифра и хотя бы одна буква. Верните <code>True</code> или <code>False</code>."},
        "starter": "def is_strong(password):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Длину строки даёт <code>len(password)</code>.",
            "<code>any(ch.isdigit() for ch in password)</code> вернёт <code>True</code>, если в пароле есть цифра.",
            "Для букв есть <code>ch.isalpha()</code>. Соедините три условия через <code>and</code>.",
        ]},
        "solution": "def is_strong(password):\n    has_digit = any(ch.isdigit() for ch in password)\n    has_letter = any(ch.isalpha() for ch in password)\n    return len(password) >= 8 and has_digit and has_letter",
        "tests": "case('is_strong(\"qwerty12\")', True)\n"
                 "case('is_strong(\"qwe12\")', False, \"Нужно не меньше 8 символов\")\n"
                 "case('is_strong(\"12345678\")', False, \"Без букв пароль не надёжный\")\n"
                 "case('is_strong(\"password\")', False, \"Без цифр пароль не надёжный\")\n"
                 "case('is_strong(\"пароль2026\")', True, \"Русские буквы тоже буквы: .isalpha()\")",
    },
    "slug": {
        "level": "medium",
        "title": {"ru": "Адрес из заголовка"},
        "text": {"ru": "Сайты превращают заголовок статьи в часть адреса: <code>Мой первый сайт</code> → <code>moy-pervyy-sayt</code>. Напишите <code>slugify(title)</code> для латиницы: оставьте буквы и цифры в нижнем регистре, всё остальное замените дефисом. Несколько дефисов подряд склейте в один, дефисы по краям уберите."},
        "starter": "def slugify(title):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Пройдите по символам <code>title.lower()</code>: буква или цифра (<code>ch.isalnum()</code>) остаётся, остальное становится <code>\"-\"</code>.",
            "Склеить части без лишних дефисов поможет <code>\"-\".join(...)</code> по непустым кускам после <code>split(\"-\")</code>.",
            "Если пишете через модуль <code>re</code>: <code>re.sub(r\"[^a-z0-9]+\", \"-\", text).strip(\"-\")</code>.",
        ]},
        "solution": "def slugify(title):\n    chars = [ch if ch.isalnum() else \"-\" for ch in title.lower()]\n    parts = \"\".join(chars).split(\"-\")\n    return \"-\".join(part for part in parts if part)",
        "tests": "case('slugify(\"Hello World\")', \"hello-world\")\n"
                 "case('slugify(\"  Flask & Django: 2 frameworks! \")', \"flask-django-2-frameworks\", \"Несколько знаков подряд дают один дефис\")\n"
                 "case('slugify(\"---\")', \"\", \"Дефисы по краям нужно убрать\")\n"
                 "case('slugify(\"Python3\")', \"python3\", \"Цифры остаются\")",
    },
    "query": {
        "level": "medium",
        "title": {"ru": "Разбор адреса"},
        "text": {"ru": "Напишите <code>parse_query(query)</code>. Она превращает строку <code>a=1&amp;b=2</code> в словарь <code>{\"a\": \"1\", \"b\": \"2\"}</code>. Части без знака <code>=</code> пропускайте. Значение может содержать <code>=</code>."},
        "starter": "def parse_query(query):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Сначала разделите строку на пары: <code>query.split(\"&amp;\")</code>.",
            "Пару без <code>=</code> пропустите проверкой <code>if \"=\" in part</code>.",
            "<code>part.split(\"=\", 1)</code> делит только по первому знаку <code>=</code>, остальные остаются в значении.",
        ]},
        "solution": "def parse_query(query):\n    result = {}\n    for part in query.split(\"&\"):\n        if \"=\" in part:\n            key, value = part.split(\"=\", 1)\n            result[key] = value\n    return result",
        "tests": "case('parse_query(\"\")', {}, \"Для пустой строки нужен пустой словарь\")\n"
                 "case('parse_query(\"a=1&b=2\")', {\"a\": \"1\", \"b\": \"2\"})\n"
                 "case('parse_query(\"flag&x=1\")', {\"x\": \"1\"}, \"Часть без = нужно пропустить\")\n"
                 "case('parse_query(\"token=a=b\")', {\"token\": \"a=b\"}, \"Делите только по первому =: split('=', 1)\")",
    },
    "router": {
        "level": "medium",
        "title": {"ru": "Простой маршрутизатор"},
        "text": {"ru": "Допишите <code>handle(method, path)</code>. Она ищет обработчик в словаре <code>ROUTES</code> и возвращает пару «код, текст». Если адреса нет, верните <code>(404, \"Not Found\")</code>. Если адрес есть, но метод не подходит, верните <code>(405, \"Method Not Allowed\")</code>."},
        "starter": "ROUTES = {\n    \"/\": {\"GET\": \"Главная\"},\n    \"/tasks\": {\"GET\": \"Список задач\", \"POST\": \"Задача создана\"},\n}\n\ndef handle(method, path):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Проверьте по порядку: сначала есть ли адрес, потом есть ли метод.",
            "<code>path not in ROUTES</code> означает, что такого адреса нет: это 404.",
            "Методы адреса лежат в <code>ROUTES[path]</code>. Если метода там нет — 405, иначе верните <code>200</code> и текст.",
        ]},
        "solution": "ROUTES = {\n    \"/\": {\"GET\": \"Главная\"},\n    \"/tasks\": {\"GET\": \"Список задач\", \"POST\": \"Задача создана\"},\n}\n\ndef handle(method, path):\n    if path not in ROUTES:\n        return 404, \"Not Found\"\n    if method not in ROUTES[path]:\n        return 405, \"Method Not Allowed\"\n    return 200, ROUTES[path][method]",
        "tests": "case('handle(\"GET\", \"/\")', (200, \"Главная\"))\n"
                 "case('handle(\"POST\", \"/tasks\")', (200, \"Задача создана\"))\n"
                 "case('handle(\"GET\", \"/nope\")', (404, \"Not Found\"), \"Для неизвестного адреса нужен код 404\")\n"
                 "case('handle(\"DELETE\", \"/\")', (405, \"Method Not Allowed\"), \"Для неподходящего метода нужен код 405\")",
    },
    "validate": {
        "level": "hard",
        "title": {"ru": "Проверка данных формы"},
        "text": {"ru": "Напишите <code>validate_user(data)</code>. Функция принимает словарь и возвращает список ошибок. Поле <code>name</code> обязательно, поле <code>age</code> должно быть целым числом от 1 до 120. Тексты ошибок: <code>\"name\"</code> и <code>\"age\"</code>. Если всё верно, верните пустой список."},
        "starter": "def validate_user(data):\n    errors = []\n    # ваш код\n    return errors",
        "hints": {"ru": [
            "Поля может не быть: <code>data.get(\"name\", \"\")</code> вернёт пустую строку вместо ошибки.",
            "Целое число проверяет <code>isinstance(age, int)</code>, диапазон — <code>1 &lt;= age &lt;= 120</code>.",
            "В Python <code>True</code> тоже считается <code>int</code>. Отсейте его отдельно: <code>isinstance(age, bool)</code>.",
        ]},
        "solution": "def validate_user(data):\n    errors = []\n    if not str(data.get(\"name\", \"\")).strip():\n        errors.append(\"name\")\n    age = data.get(\"age\")\n    if not isinstance(age, int) or isinstance(age, bool) or not 1 <= age <= 120:\n        errors.append(\"age\")\n    return errors",
        "tests": "case('validate_user({\"name\": \"Аружан\", \"age\": 20})', [], \"Верные данные не должны давать ошибок\")\n"
                 "case('validate_user({\"age\": 20})', [\"name\"], \"Без имени должна быть ошибка name\")\n"
                 "case('validate_user({\"name\": \"  \", \"age\": 20})', [\"name\"], \"Имя из пробелов считается пустым\")\n"
                 "case('validate_user({\"name\": \"A\", \"age\": 0})', [\"age\"], \"Возраст 0 не подходит\")\n"
                 "case('validate_user({\"name\": \"A\", \"age\": \"20\"})', [\"age\"], \"Строка не считается числом\")\n"
                 "case('validate_user({\"name\": \"A\", \"age\": True})', [\"age\"], \"True в Python тоже int: проверьте это отдельно\")\n"
                 "case('validate_user({})', [\"name\", \"age\"], \"Нужно вернуть обе ошибки по порядку\")",
    },
    "json": {
        "level": "medium",
        "title": {"ru": "Ответ в JSON"},
        "text": {"ru": "Напишите <code>tasks_json(tasks)</code>. Функция получает список словарей и возвращает строку JSON только с задачами, у которых <code>done</code> равно <code>False</code>. Кириллица должна остаться читаемой. Импорт уже есть."},
        "starter": "import json\n\ndef tasks_json(tasks):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Отберите невыполненные задачи: <code>[task for task in tasks if not task[\"done\"]]</code>.",
            "Список превращается в строку JSON функцией <code>json.dumps(...)</code>.",
            "Чтобы кириллица не стала кодами вида <code>\\u041a</code>, добавьте <code>ensure_ascii=False</code>.",
        ]},
        "solution": "import json\n\ndef tasks_json(tasks):\n    active = [task for task in tasks if not task[\"done\"]]\n    return json.dumps(active, ensure_ascii=False)",
        "tests": "data = [{\"title\": \"Код\", \"done\": False}, {\"title\": \"Сон\", \"done\": True}]\n"
                 "case('type(tasks_json(data)).__name__', \"str\", \"Нужно вернуть строку, а не список\")\n"
                 "case('json.loads(tasks_json(data))', [{\"title\": \"Код\", \"done\": False}], \"В ответе должны остаться только невыполненные задачи\")\n"
                 "case('\"Код\" in tasks_json(data)', True, \"Добавьте ensure_ascii=False, иначе кириллица превратится в коды\")\n"
                 "case('tasks_json([])', \"[]\", \"Для пустого списка нужна строка []\")",
    },
    "render": {
        "level": "medium",
        "title": {"ru": "Свой шаблон"},
        "text": {"ru": "Шаблон — текст с пропусками. Напишите <code>render(template, data)</code>: она заменяет каждый пропуск <code>{{ имя }}</code> на значение из словаря <code>data</code>. Пробелы внутри скобок могут быть или не быть. Если ключа в словаре нет, подставьте пустую строку."},
        "starter": "import re\n\ndef render(template, data):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Найти все пропуски поможет регулярное выражение <code>r\"\\{\\{\\s*(\\w+)\\s*\\}\\}\"</code>.",
            "<code>re.sub(шаблон, функция, текст)</code> вызывает функцию для каждого найденного пропуска и подставляет её ответ.",
            "Внутри функции имя пропуска лежит в <code>match.group(1)</code>, а значение достаёт <code>str(data.get(имя, \"\"))</code>.",
        ]},
        "solution": "import re\n\ndef render(template, data):\n    def value(match):\n        return str(data.get(match.group(1), \"\"))\n    return re.sub(r\"\\{\\{\\s*(\\w+)\\s*\\}\\}\", value, template)",
        "tests": "case('render(\"Привет, {{ name }}!\", {\"name\": \"Дана\"})', \"Привет, Дана!\")\n"
                 "case('render(\"{{a}}+{{ b }}={{c}}\", {\"a\": 1, \"b\": 2, \"c\": 3})', \"1+2=3\", \"Пробелы внутри скобок необязательны, числа превратите в строку\")\n"
                 "case('render(\"[{{ missing }}]\", {})', \"[]\", \"Неизвестный ключ заменяется пустой строкой\")\n"
                 "case('render(\"без пропусков\", {\"x\": 1})', \"без пропусков\")",
    },
    "paginate": {
        "level": "medium",
        "title": {"ru": "Страницы списка"},
        "text": {"ru": "Длинный список показывают по частям. Напишите <code>paginate(items, page, per_page)</code>: верните элементы страницы номер <code>page</code> (нумерация с 1). Если страницы с таким номером нет или номер меньше 1, верните пустой список."},
        "starter": "def paginate(items, page, per_page):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Первый элемент страницы стоит на месте <code>(page - 1) * per_page</code>.",
            "Срез <code>items[start:start + per_page]</code> сам обрежется, если элементов меньше.",
            "Номер страницы меньше 1 проверьте отдельно, иначе отрицательный срез вернёт лишнее.",
        ]},
        "solution": "def paginate(items, page, per_page):\n    if page < 1:\n        return []\n    start = (page - 1) * per_page\n    return items[start:start + per_page]",
        "tests": "letters = list(\"abcdefg\")\n"
                 "case('paginate(letters, 1, 3)', [\"a\", \"b\", \"c\"])\n"
                 "case('paginate(letters, 3, 3)', [\"g\"], \"На последней странице может быть меньше элементов\")\n"
                 "case('paginate(letters, 4, 3)', [], \"Такой страницы нет: нужен пустой список\")\n"
                 "case('paginate(letters, 0, 3)', [], \"Страницы с номером 0 не бывает\")",
    },
    "add_task": {
        "level": "medium",
        "title": {"ru": "Безопасная вставка"},
        "text": {"ru": "Напишите <code>add_task(db, title)</code>: она добавляет строку в таблицу <code>tasks</code> и возвращает её <code>id</code>. Используйте параметр <code>?</code>: текст с кавычкой не должен ломать запрос."},
        "starter": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT)\")\n\ndef add_task(db, title):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Запрос на вставку: <code>INSERT INTO tasks (title) VALUES (?)</code>.",
            "Значения передаются вторым аргументом кортежем: <code>db.execute(запрос, (title,))</code>. Запятая после <code>title</code> обязательна.",
            "<code>execute</code> возвращает курсор, а номер новой строки лежит в <code>cursor.lastrowid</code>. Не забудьте <code>db.commit()</code>.",
        ]},
        "solution": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT)\")\n\ndef add_task(db, title):\n    cursor = db.execute(\"INSERT INTO tasks (title) VALUES (?)\", (title,))\n    db.commit()\n    return cursor.lastrowid",
        "tests": "case('add_task(db, \"Первая\")', 1, \"Верните cursor.lastrowid\")\n"
                 "case('add_task(db, \"Вторая\")', 2, \"Каждая новая строка получает следующий id\")\n"
                 "evil = \"x'); DROP TABLE tasks; --\"\n"
                 "case('add_task(db, evil)', 3, \"Текст с кавычкой не должен ломать запрос: используйте ?\")\n"
                 "case('db.execute(\"SELECT title FROM tasks WHERE id = 3\").fetchone()', (evil,), \"Текст с кавычкой должен сохраниться как есть\")",
    },
    "select": {
        "level": "easy",
        "title": {"ru": "Выборка с условием"},
        "text": {"ru": "Напишите <code>active_titles(db)</code>: верните список заголовков, у которых <code>done = 0</code>, отсортированный по алфавиту."},
        "starter": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (title TEXT, done INTEGER)\")\ndb.executemany(\"INSERT INTO tasks VALUES (?, ?)\", [(\"Б\", 0), (\"А\", 0), (\"В\", 1)])\n\ndef active_titles(db):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Нужен запрос <code>SELECT title FROM tasks</code> с условием <code>WHERE done = 0</code>.",
            "Сортировку по алфавиту даёт <code>ORDER BY title</code> в конце запроса.",
            "Каждая строка результата — кортеж, заголовок в нём первый: <code>[row[0] for row in rows]</code>.",
        ]},
        "solution": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (title TEXT, done INTEGER)\")\ndb.executemany(\"INSERT INTO tasks VALUES (?, ?)\", [(\"Б\", 0), (\"А\", 0), (\"В\", 1)])\n\ndef active_titles(db):\n    rows = db.execute(\"SELECT title FROM tasks WHERE done = 0 ORDER BY title\")\n    return [row[0] for row in rows]",
        "tests": "case('active_titles(db)', [\"А\", \"Б\"], \"Добавьте WHERE и ORDER BY и верните список строк\")\n"
                 "db.execute(\"UPDATE tasks SET done = 1\")\n"
                 "case('active_titles(db)', [], \"Если подходящих строк нет, верните пустой список\")",
    },
    "route": {
        "level": "easy",
        "title": {"ru": "Первый маршрут"},
        "text": {"ru": "Добавьте маршрут <code>GET /hello/&lt;name&gt;</code>, который возвращает JSON <code>{\"message\": \"Привет, имя!\"}</code>."},
        "starter": "from flask import Flask\n\napp = Flask(__name__)\n\n# ваш маршрут",
        "hints": {"ru": [
            "Маршрут объявляют декоратором над функцией: <code>@app.get(\"/hello/&lt;name&gt;\")</code>.",
            "Имя в угловых скобках адреса и имя аргумента функции должны совпадать: <code>def hello(name):</code>.",
            "Если вернуть словарь, Flask сам превратит его в JSON: <code>return {\"message\": f\"Привет, {name}!\"}</code>.",
        ]},
        "solution": "from flask import Flask\n\napp = Flask(__name__)\n\n@app.get(\"/hello/<name>\")\ndef hello(name):\n    return {\"message\": f\"Привет, {name}!\"}",
        "tests": "client = app.test_client()\n"
                 "case('client.get(\"/hello/Python\").status_code', 200, \"Адрес /hello/Python должен открываться с кодом 200\")\n"
                 "case('client.get(\"/hello/Python\").json', {\"message\": \"Привет, Python!\"})",
    },
    "filter": {
        "level": "medium",
        "title": {"ru": "Фильтр в адресе"},
        "text": {"ru": "Сделайте <code>GET /tasks</code>, который возвращает JSON-список задач из <code>TASKS</code>. Если в адресе есть <code>?done=1</code>, верните только выполненные, если <code>?done=0</code> — только невыполненные. Без параметра верните все."},
        "starter": "from flask import Flask, request\n\napp = Flask(__name__)\nTASKS = [\n    {\"title\": \"Купить хлеб\", \"done\": True},\n    {\"title\": \"Выучить Flask\", \"done\": False},\n]\n\n# ваш маршрут",
        "hints": {"ru": [
            "Параметр из адреса читает <code>request.args.get(\"done\")</code>. Если его нет, будет <code>None</code>.",
            "Параметр приходит строкой: сравнивайте с <code>\"1\"</code>, а не с числом.",
            "Список словарей Flask превращает в JSON сам, если вернуть его из функции.",
        ]},
        "solution": "from flask import Flask, request\n\napp = Flask(__name__)\nTASKS = [\n    {\"title\": \"Купить хлеб\", \"done\": True},\n    {\"title\": \"Выучить Flask\", \"done\": False},\n]\n\n@app.get(\"/tasks\")\ndef tasks():\n    done = request.args.get(\"done\")\n    if done is None:\n        return TASKS\n    return [task for task in TASKS if task[\"done\"] == (done == \"1\")]",
        "tests": "client = app.test_client()\n"
                 "case('len(client.get(\"/tasks\").json)', 2, \"Без параметра нужны все задачи\")\n"
                 "case('client.get(\"/tasks?done=1\").json', [{\"title\": \"Купить хлеб\", \"done\": True}], \"?done=1 — только выполненные\")\n"
                 "case('client.get(\"/tasks?done=0\").json', [{\"title\": \"Выучить Flask\", \"done\": False}], \"?done=0 — только невыполненные: параметр приходит строкой\")",
    },
    "post": {
        "level": "hard",
        "title": {"ru": "Создание записи"},
        "text": {"ru": "Сделайте <code>POST /items</code>. Он читает JSON с полем <code>title</code>. Если поля нет или оно пустое, верните <code>{\"error\": \"title\"}</code> с кодом 400. Иначе добавьте заголовок в список <code>items</code> и верните <code>{\"title\": ...}</code> с кодом 201."},
        "starter": "from flask import Flask, request\n\napp = Flask(__name__)\nitems = []\n\n# ваш маршрут",
        "hints": {"ru": [
            "Маршрут для отправки данных объявляют через <code>@app.post(\"/items\")</code>.",
            "<code>request.get_json(silent=True) or {}</code> не падает, если прислали не JSON, а даёт пустой словарь.",
            "Код ответа ставится вторым значением: <code>return {\"error\": \"title\"}, 400</code>.",
        ]},
        "solution": "from flask import Flask, request\n\napp = Flask(__name__)\nitems = []\n\n@app.post(\"/items\")\ndef create_item():\n    data = request.get_json(silent=True) or {}\n    title = str(data.get(\"title\", \"\")).strip()\n    if not title:\n        return {\"error\": \"title\"}, 400\n    items.append(title)\n    return {\"title\": title}, 201",
        "tests": "client = app.test_client()\n"
                 "case('client.post(\"/items\", json={}).status_code', 400, \"Без title нужен код 400\")\n"
                 "case('client.post(\"/items\", json={\"title\": \"  \"}).status_code', 400, \"Пустой title тоже даёт 400\")\n"
                 "case('client.post(\"/items\", data=\"не json\").status_code', 400, \"Неверный JSON не должен приводить к падению: get_json(silent=True)\")\n"
                 "case('client.post(\"/items\", json={\"title\": \"Книга\"}).status_code', 201, \"При успехе нужен код 201: return {...}, 201\")\n"
                 "case('items', [\"Книга\"], \"Заголовок должен попасть в список items\")\n"
                 "case('client.post(\"/items\", json={\"title\": \"Ручка\"}).json', {\"title\": \"Ручка\"})",
    },
    "detail": {
        "level": "hard",
        "title": {"ru": "Одна запись или 404"},
        "text": {"ru": "Сделайте <code>GET /tasks/&lt;int:task_id&gt;</code>. Если задача с таким номером есть в словаре <code>TASKS</code>, верните её JSON. Если нет, верните <code>{\"error\": \"not found\"}</code> с кодом 404."},
        "starter": "from flask import Flask\n\napp = Flask(__name__)\nTASKS = {\n    1: {\"id\": 1, \"title\": \"Купить хлеб\"},\n    2: {\"id\": 2, \"title\": \"Выучить Flask\"},\n}\n\n# ваш маршрут",
        "hints": {"ru": [
            "<code>&lt;int:task_id&gt;</code> в адресе превращает часть пути в число и передаёт его в функцию.",
            "<code>TASKS.get(task_id)</code> вернёт <code>None</code>, если такой задачи нет.",
            "Для отсутствующей задачи: <code>return {\"error\": \"not found\"}, 404</code>.",
        ]},
        "solution": "from flask import Flask\n\napp = Flask(__name__)\nTASKS = {\n    1: {\"id\": 1, \"title\": \"Купить хлеб\"},\n    2: {\"id\": 2, \"title\": \"Выучить Flask\"},\n}\n\n@app.get(\"/tasks/<int:task_id>\")\ndef task_detail(task_id):\n    task = TASKS.get(task_id)\n    if task is None:\n        return {\"error\": \"not found\"}, 404\n    return task",
        "tests": "client = app.test_client()\n"
                 "case('client.get(\"/tasks/2\").json', {\"id\": 2, \"title\": \"Выучить Flask\"})\n"
                 "case('client.get(\"/tasks/99\").status_code', 404, \"Для несуществующей задачи нужен код 404\")\n"
                 "case('client.get(\"/tasks/99\").json', {\"error\": \"not found\"})\n"
                 "case('client.get(\"/tasks/abc\").status_code', 404, \"<int:...> пропускает только числа\")",
    },
    "total": {
        "level": "easy",
        "title": {"ru": "Сумма покупок"},
        "text": {"ru": "Напишите <code>total(prices)</code>: функция получает список цен и возвращает их сумму. Для пустого списка верните <code>0</code>."},
        "starter": "def total(prices):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Заведите переменную <code>result = 0</code> и прибавляйте к ней каждую цену в цикле <code>for</code>.",
            "Короткий путь: встроенная функция <code>sum(prices)</code> делает то же самое.",
        ]},
        "solution": "def total(prices):\n    result = 0\n    for price in prices:\n        result += price\n    return result",
        "tests": "case('total([100, 250, 50])', 400)\ncase('total([])', 0)\ncase('total([1.5, 2.5])', 4.0)",
    },
    "evens": {
        "level": "easy",
        "title": {"ru": "Только чётные"},
        "text": {"ru": "Напишите <code>only_even(numbers)</code>: верните новый список, в котором остались только чётные числа в том же порядке."},
        "starter": "def only_even(numbers):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Число чётное, если остаток от деления на 2 равен нулю: <code>n % 2 == 0</code>.",
            "Начните с пустого списка и добавляйте подходящие числа через <code>.append(n)</code>.",
        ]},
        "solution": "def only_even(numbers):\n    return [n for n in numbers if n % 2 == 0]",
        "tests": "case('only_even([1, 2, 3, 4])', [2, 4])\ncase('only_even([7, 9])', [])\ncase('only_even([0, -2, 5])', [0, -2])",
    },
    "truncate": {
        "level": "easy",
        "title": {"ru": "Короткий анонс"},
        "text": {"ru": "Напишите <code>truncate(text, limit)</code>. Если текст не длиннее <code>limit</code> символов, верните его как есть. Иначе верните первые <code>limit</code> символов и три точки <code>...</code>."},
        "starter": "def truncate(text, limit):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Первые символы строки даёт срез: <code>text[:limit]</code>.",
            "Сначала проверьте длину: <code>if len(text) &lt;= limit</code>.",
        ]},
        "solution": "def truncate(text, limit):\n    if len(text) <= limit:\n        return text\n    return text[:limit] + \"...\"",
        "tests": "case('truncate(\"Python\", 10)', \"Python\")\ncase('truncate(\"Python for the web\", 6)', \"Python...\")\ncase('truncate(\"Flask\", 5)', \"Flask\")",
    },
    "longest": {
        "level": "medium",
        "title": {"ru": "Самое длинное слово"},
        "text": {"ru": "Напишите <code>longest(words)</code>: верните самое длинное слово из списка. Если таких несколько, верните первое из них. Для пустого списка верните пустую строку."},
        "starter": "def longest(words):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Храните лучшее слово в переменной <code>best = \"\"</code> и сравнивайте длины через <code>len()</code>.",
            "Чтобы при равной длине осталось первое слово, сравнивайте строго: <code>len(word) &gt; len(best)</code>.",
        ]},
        "solution": "def longest(words):\n    best = \"\"\n    for word in words:\n        if len(word) > len(best):\n            best = word\n    return best",
        "tests": "case('longest([\"api\", \"python\", \"web\"])', \"python\")\ncase('longest([\"html\", \"json\"])', \"html\")\ncase('longest([])', \"\")",
    },
    "unique": {
        "level": "medium",
        "title": {"ru": "Без повторов"},
        "text": {"ru": "Напишите <code>unique(items)</code>: верните список без повторов. Порядок первых появлений должен сохраниться."},
        "starter": "def unique(items):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Проверить, есть ли элемент в списке, можно через <code>item not in result</code>.",
            "Через <code>set()</code> повторы уйдут, но порядок может измениться, поэтому здесь нужен цикл.",
        ]},
        "solution": "def unique(items):\n    result = []\n    for item in items:\n        if item not in result:\n            result.append(item)\n    return result",
        "tests": "case('unique([\"a\", \"b\", \"a\", \"c\", \"b\"])', [\"a\", \"b\", \"c\"])\ncase('unique([3, 3, 3])', [3])\ncase('unique([])', [])",
    },
    "initials": {
        "level": "medium",
        "title": {"ru": "Инициалы"},
        "text": {"ru": "Напишите <code>initials(full_name)</code>: из имени и фамилии сделайте инициалы. Из <code>Aru Bekova</code> должно получиться <code>A. B.</code> Буквы делайте заглавными, лишние пробелы не учитывайте."},
        "starter": "def initials(full_name):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "<code>full_name.split()</code> делит строку на слова и сам убирает лишние пробелы.",
            "Первая буква слова — <code>part[0]</code>, заглавной её делает <code>.upper()</code>. Соберите части через <code>\" \".join(...)</code>.",
        ]},
        "solution": "def initials(full_name):\n    parts = full_name.split()\n    return \" \".join(part[0].upper() + \".\" for part in parts)",
        "tests": "case('initials(\"Aru Bekova\")', \"A. B.\")\ncase('initials(\"  dana   ali \")', \"D. A.\")\ncase('initials(\"Python\")', \"P.\")",
    },
    "status": {
        "level": "easy",
        "title": {"ru": "Текст статуса"},
        "text": {"ru": "Напишите <code>status_text(code)</code>: по коду ответа верните его название. <code>200</code> — <code>OK</code>, <code>201</code> — <code>Created</code>, <code>404</code> — <code>Not Found</code>, <code>500</code> — <code>Internal Server Error</code>. Для остальных кодов верните <code>Unknown</code>."},
        "starter": "def status_text(code):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Удобно хранить пары в словаре: <code>{200: \"OK\", 404: \"Not Found\"}</code>.",
            "<code>names.get(code, \"Unknown\")</code> вернёт запасное значение, если кода нет в словаре.",
        ]},
        "solution": "def status_text(code):\n    names = {200: \"OK\", 201: \"Created\", 404: \"Not Found\", 500: \"Internal Server Error\"}\n    return names.get(code, \"Unknown\")",
        "tests": "case('status_text(200)', \"OK\")\ncase('status_text(201)', \"Created\")\ncase('status_text(404)', \"Not Found\")\ncase('status_text(500)', \"Internal Server Error\")\ncase('status_text(418)', \"Unknown\")",
    },
    "mime": {
        "level": "medium",
        "title": {"ru": "Тип файла"},
        "text": {"ru": "Сервер сообщает браузеру тип файла в заголовке <code>Content-Type</code>. Напишите <code>content_type(filename)</code>: для <code>.html</code> верните <code>text/html</code>, для <code>.css</code> — <code>text/css</code>, для <code>.js</code> — <code>text/javascript</code>, для <code>.json</code> — <code>application/json</code>, для остальных — <code>application/octet-stream</code>. Регистр букв в имени не важен."},
        "starter": "def content_type(filename):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Расширение — это часть после последней точки: <code>filename.rsplit(\".\", 1)[-1]</code>.",
            "Приведите имя к нижнему регистру через <code>.lower()</code> и возьмите тип из словаря через <code>.get()</code> с запасным значением.",
        ]},
        "solution": "def content_type(filename):\n    types = {\"html\": \"text/html\", \"css\": \"text/css\", \"js\": \"text/javascript\", \"json\": \"application/json\"}\n    extension = filename.lower().rsplit(\".\", 1)[-1]\n    return types.get(extension, \"application/octet-stream\")",
        "tests": "case('content_type(\"index.html\")', \"text/html\")\ncase('content_type(\"styles.css\")', \"text/css\")\ncase('content_type(\"app.min.js\")', \"text/javascript\")\ncase('content_type(\"DATA.JSON\")', \"application/json\")\ncase('content_type(\"photo.png\")', \"application/octet-stream\")",
    },
    "build_url": {
        "level": "medium",
        "title": {"ru": "Адрес с параметрами"},
        "text": {"ru": "Напишите <code>build_url(path, params)</code>: добавьте к пути параметры из словаря. Из <code>\"/search\"</code> и <code>{\"q\": \"flask\", \"page\": 2}</code> должно получиться <code>/search?q=flask&amp;page=2</code>. Если словарь пустой, верните путь без знака вопроса."},
        "starter": "def build_url(path, params):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Пары ключ и значение даёт <code>params.items()</code>. Каждую превратите в строку <code>f\"{key}={value}\"</code>.",
            "Соедините пары через <code>\"&amp;\".join(pairs)</code> и добавьте к пути после знака <code>?</code>.",
        ]},
        "solution": "def build_url(path, params):\n    if not params:\n        return path\n    pairs = [f\"{key}={value}\" for key, value in params.items()]\n    return path + \"?\" + \"&\".join(pairs)",
        "tests": "case('build_url(\"/search\", {\"q\": \"flask\", \"page\": 2})', \"/search?q=flask&page=2\")\ncase('build_url(\"/tasks\", {})', \"/tasks\")\ncase('build_url(\"/\", {\"lang\": \"kk\"})', \"/?lang=kk\")",
    },
    "cookie": {
        "level": "medium",
        "title": {"ru": "Разбор cookie"},
        "text": {"ru": "Напишите <code>parse_cookie(header)</code>: превратите строку заголовка <code>theme=dark; lang=kk</code> в словарь <code>{\"theme\": \"dark\", \"lang\": \"kk\"}</code>. Для пустой строки верните пустой словарь. В значении может встретиться знак <code>=</code>."},
        "starter": "def parse_cookie(header):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Сначала разделите строку по <code>;</code>, затем у каждой части уберите пробелы через <code>.strip()</code>.",
            "<code>part.split(\"=\", 1)</code> делит только по первому знаку равно, поэтому значение <code>a=b</code> останется целым.",
        ]},
        "solution": "def parse_cookie(header):\n    result = {}\n    for part in header.split(\";\"):\n        if \"=\" in part:\n            key, value = part.strip().split(\"=\", 1)\n            result[key] = value\n    return result",
        "tests": "case('parse_cookie(\"theme=dark; lang=kk\")', {\"theme\": \"dark\", \"lang\": \"kk\"})\ncase('parse_cookie(\"\")', {})\ncase('parse_cookie(\"token=a=b\")', {\"token\": \"a=b\"})",
    },
    "redirect": {
        "level": "medium",
        "title": {"ru": "Безопасный переход"},
        "text": {"ru": "После входа сайт возвращает человека на адрес из параметра <code>next</code>. Напишите <code>is_safe_redirect(url)</code>: верните <code>True</code>, только если адрес ведёт на этот же сайт, то есть начинается с одной косой черты <code>/</code>. Адрес <code>//evil.example</code> браузер считает чужим сайтом."},
        "starter": "def is_safe_redirect(url):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Начало строки проверяет <code>url.startswith(\"/\")</code>.",
            "Добавьте второе условие через <code>and not</code>: адрес не должен начинаться с <code>//</code>.",
        ]},
        "solution": "def is_safe_redirect(url):\n    return url.startswith(\"/\") and not url.startswith(\"//\")",
        "tests": "case('is_safe_redirect(\"/profile\")', True)\ncase('is_safe_redirect(\"https://evil.example\")', False)\ncase('is_safe_redirect(\"//evil.example\")', False)\ncase('is_safe_redirect(\"\")', False)",
    },
    "clean": {
        "level": "easy",
        "title": {"ru": "Чистый заголовок"},
        "text": {"ru": "Напишите <code>clean_title(value)</code>: уберите пробелы по краям, а несколько пробелов подряд внутри замените одним. Из <code>\"  Buy   bread \"</code> должно получиться <code>Buy bread</code>."},
        "starter": "def clean_title(value):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "<code>value.split()</code> без аргументов делит строку по любым пробелам и отбрасывает пустые части.",
            "Соберите слова обратно через <code>\" \".join(...)</code>.",
        ]},
        "solution": "def clean_title(value):\n    return \" \".join(value.split())",
        "tests": "case('clean_title(\"  Buy   bread \")', \"Buy bread\")\ncase('clean_title(\"Flask\")', \"Flask\")\ncase('clean_title(\"   \")', \"\")",
    },
    "to_int": {
        "level": "medium",
        "title": {"ru": "Число из формы"},
        "text": {"ru": "Поля формы всегда приходят строками. Напишите <code>to_int(value, default)</code>: превратите строку в целое число. Пробелы по краям не мешают. Если в строке не число, верните <code>default</code>."},
        "starter": "def to_int(value, default):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "<code>int(\"abc\")</code> вызывает ошибку <code>ValueError</code>. Её ловит блок <code>try</code> / <code>except ValueError</code>.",
            "В блоке <code>except</code> просто верните запасное значение: <code>return default</code>.",
        ]},
        "solution": "def to_int(value, default):\n    try:\n        return int(value.strip())\n    except ValueError:\n        return default",
        "tests": "case('to_int(\"42\", 0)', 42)\ncase('to_int(\" 7 \", 0)', 7)\ncase('to_int(\"abc\", 1)', 1)\ncase('to_int(\"\", 5)', 5)\ncase('to_int(\"-3\", 0)', -3)",
    },
    "missing": {
        "level": "medium",
        "title": {"ru": "Обязательные поля"},
        "text": {"ru": "Напишите <code>missing_fields(data, required)</code>. <code>data</code> — словарь с данными формы, <code>required</code> — список обязательных полей. Верните список тех полей, которых нет в словаре или которые пустые. Строка из одних пробелов тоже пустая. Порядок — как в <code>required</code>."},
        "starter": "def missing_fields(data, required):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "<code>data.get(name, \"\")</code> вернёт пустую строку, если поля нет.",
            "Пустоту проверяет <code>not value.strip()</code>: у строки из пробелов после <code>.strip()</code> ничего не остаётся.",
        ]},
        "solution": "def missing_fields(data, required):\n    return [name for name in required if not str(data.get(name, \"\")).strip()]",
        "tests": "case('missing_fields({\"name\": \"Aru\", \"email\": \"\"}, [\"name\", \"email\"])', [\"email\"])\ncase('missing_fields({}, [\"name\", \"email\"])', [\"name\", \"email\"])\ncase('missing_fields({\"name\": \"  \"}, [\"name\"])', [\"name\"])\ncase('missing_fields({\"name\": \"Aru\"}, [\"name\"])', [])",
    },
    "escape": {
        "level": "medium",
        "title": {"ru": "Безопасный вывод"},
        "text": {"ru": "Напишите <code>escape_html(text)</code>: замените знак <code>&amp;</code> на <code>&amp;amp;</code>, <code>&lt;</code> на <code>&amp;lt;</code>, <code>&gt;</code> на <code>&amp;gt;</code>. Тогда текст пользователя покажется на странице как текст и не станет тегом."},
        "starter": "def escape_html(text):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Замену делает <code>text.replace(\"&lt;\", \"&amp;lt;\")</code>. Результат нужно сохранить: строки не меняются на месте.",
            "Начните со знака <code>&amp;</code>. Иначе он заменится второй раз внутри уже готовых <code>&amp;lt;</code>.",
        ]},
        "solution": "def escape_html(text):\n    text = text.replace(\"&\", \"&amp;\")\n    text = text.replace(\"<\", \"&lt;\")\n    return text.replace(\">\", \"&gt;\")",
        "tests": "case('escape_html(\"<b>hi</b>\")', \"&lt;b&gt;hi&lt;/b&gt;\")\ncase('escape_html(\"Tom & Jerry\")', \"Tom &amp; Jerry\")\ncase('escape_html(\"a < b\")', \"a &lt; b\")\ncase('escape_html(\"&lt;\")', \"&amp;lt;\")",
    },
    "email": {
        "level": "hard",
        "title": {"ru": "Похоже на почту"},
        "text": {"ru": "Напишите <code>is_email(value)</code>: грубая проверка адреса почты. В адресе нет пробелов, ровно один знак <code>@</code>, перед ним есть хотя бы один символ, а после него есть точка, которая стоит не в начале и не в конце."},
        "starter": "def is_email(value):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Сколько раз встречается символ, считает <code>value.count(\"@\")</code>.",
            "Разделите адрес на две части: <code>name, domain = value.split(\"@\")</code>, и проверьте каждую отдельно.",
        ]},
        "solution": "def is_email(value):\n    if \" \" in value or value.count(\"@\") != 1:\n        return False\n    name, domain = value.split(\"@\")\n    if not name or \".\" not in domain:\n        return False\n    return not domain.startswith(\".\") and not domain.endswith(\".\")",
        "tests": "case('is_email(\"aru@example.com\")', True)\ncase('is_email(\"aru.example.com\")', False)\ncase('is_email(\"a@b@example.com\")', False)\ncase('is_email(\"@example.com\")', False)\ncase('is_email(\"aru@example\")', False)\ncase('is_email(\"aru @example.com\")', False)\ncase('is_email(\"aru@example.\")', False)",
    },
    "count": {
        "level": "easy",
        "title": {"ru": "Сколько осталось"},
        "text": {"ru": "Напишите <code>count_active(db)</code>: верните число задач, у которых <code>done = 0</code>. Считать должна база, а не Python."},
        "starter": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER)\")\ndb.executemany(\"INSERT INTO tasks (title, done) VALUES (?, ?)\", [(\"Buy bread\", 1), (\"Learn Flask\", 0), (\"Write tests\", 0)])\n\ndef count_active(db):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Строки считает запрос <code>SELECT COUNT(*) FROM tasks WHERE done = 0</code>.",
            "<code>.fetchone()</code> вернёт одну строку-кортеж, число в ней первое: <code>row[0]</code>.",
        ]},
        "solution": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER)\")\ndb.executemany(\"INSERT INTO tasks (title, done) VALUES (?, ?)\", [(\"Buy bread\", 1), (\"Learn Flask\", 0), (\"Write tests\", 0)])\n\ndef count_active(db):\n    row = db.execute(\"SELECT COUNT(*) FROM tasks WHERE done = 0\").fetchone()\n    return row[0]",
        "tests": "case('count_active(db)', 2)\ndb.execute(\"UPDATE tasks SET done = 1\")\ncase('count_active(db)', 0)",
    },
    "delete_done": {
        "level": "easy",
        "title": {"ru": "Удалить выполненные"},
        "text": {"ru": "Напишите <code>delete_done(db)</code>: удалите все выполненные задачи (<code>done = 1</code>) и верните, сколько строк удалено."},
        "starter": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER)\")\ndb.executemany(\"INSERT INTO tasks (title, done) VALUES (?, ?)\", [(\"Buy bread\", 1), (\"Learn Flask\", 0), (\"Write tests\", 0)])\n\ndef delete_done(db):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Запрос на удаление: <code>DELETE FROM tasks WHERE done = 1</code>.",
            "Число удалённых строк лежит в <code>cursor.rowcount</code>. Не забудьте <code>db.commit()</code>.",
        ]},
        "solution": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER)\")\ndb.executemany(\"INSERT INTO tasks (title, done) VALUES (?, ?)\", [(\"Buy bread\", 1), (\"Learn Flask\", 0), (\"Write tests\", 0)])\n\ndef delete_done(db):\n    cursor = db.execute(\"DELETE FROM tasks WHERE done = 1\")\n    db.commit()\n    return cursor.rowcount",
        "tests": "case('delete_done(db)', 1)\ncase('db.execute(\"SELECT COUNT(*) FROM tasks\").fetchone()', (2,))\ncase('delete_done(db)', 0)",
    },
    "mark_done": {
        "level": "medium",
        "title": {"ru": "Отметить выполненной"},
        "text": {"ru": "Напишите <code>mark_done(db, task_id)</code>: поставьте задаче с этим номером <code>done = 1</code>. Верните <code>True</code>, если такая задача была, и <code>False</code>, если её нет. Остальные задачи менять нельзя."},
        "starter": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER)\")\ndb.executemany(\"INSERT INTO tasks (title, done) VALUES (?, ?)\", [(\"Buy bread\", 1), (\"Learn Flask\", 0), (\"Write tests\", 0)])\n\ndef mark_done(db, task_id):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Запрос на изменение: <code>UPDATE tasks SET done = 1 WHERE id = ?</code>. Без <code>WHERE</code> изменятся все строки.",
            "Сколько строк изменилось, показывает <code>cursor.rowcount</code>.",
        ]},
        "solution": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER)\")\ndb.executemany(\"INSERT INTO tasks (title, done) VALUES (?, ?)\", [(\"Buy bread\", 1), (\"Learn Flask\", 0), (\"Write tests\", 0)])\n\ndef mark_done(db, task_id):\n    cursor = db.execute(\"UPDATE tasks SET done = 1 WHERE id = ?\", (task_id,))\n    db.commit()\n    return cursor.rowcount == 1",
        "tests": "case('mark_done(db, 2)', True)\ncase('db.execute(\"SELECT done FROM tasks WHERE id = 2\").fetchone()', (1,))\ncase('db.execute(\"SELECT done FROM tasks WHERE id = 3\").fetchone()', (0,))\ncase('mark_done(db, 99)', False)",
    },
    "search": {
        "level": "hard",
        "title": {"ru": "Поиск по тексту"},
        "text": {"ru": "Напишите <code>search(db, text)</code>: верните заголовки задач, в которых встречается <code>text</code>, в порядке <code>id</code>. Текст передавайте через параметр <code>?</code>, чтобы кавычка в поиске не сломала запрос."},
        "starter": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER)\")\ndb.executemany(\"INSERT INTO tasks (title, done) VALUES (?, ?)\", [(\"Buy bread\", 1), (\"Learn Flask\", 0), (\"Write tests\", 0)])\n\ndef search(db, text):\n    # ваш код\n    pass",
        "hints": {"ru": [
            "Поиск по части строки делает <code>WHERE title LIKE ?</code>, а знак <code>%</code> означает «любые символы».",
            "Знаки процента добавьте к значению, а не к запросу: <code>(\"%\" + text + \"%\",)</code>.",
        ]},
        "solution": "import sqlite3\n\ndb = sqlite3.connect(\":memory:\")\ndb.execute(\"CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER)\")\ndb.executemany(\"INSERT INTO tasks (title, done) VALUES (?, ?)\", [(\"Buy bread\", 1), (\"Learn Flask\", 0), (\"Write tests\", 0)])\n\ndef search(db, text):\n    rows = db.execute(\"SELECT title FROM tasks WHERE title LIKE ? ORDER BY id\", (\"%\" + text + \"%\",))\n    return [row[0] for row in rows]",
        "tests": "case('search(db, \"Flask\")', [\"Learn Flask\"])\ncase('search(db, \"e\")', [\"Buy bread\", \"Learn Flask\", \"Write tests\"])\ncase('search(db, \"django\")', [])\ncase('search(db, \"x\\'; DROP TABLE tasks; --\")', [])\ncase('db.execute(\"SELECT COUNT(*) FROM tasks\").fetchone()', (3,))",
    },
    "health": {
        "level": "easy",
        "title": {"ru": "Проверка связи"},
        "text": {"ru": "Добавьте маршрут <code>GET /health</code>, который возвращает JSON <code>{\"status\": \"ok\"}</code>. Такой адрес делают, чтобы проверять, жив ли сервер. На <code>POST</code> он отвечать не должен."},
        "starter": "from flask import Flask\n\napp = Flask(__name__)\n\n# ваш маршрут",
        "hints": {"ru": [
            "Маршрут только для GET объявляют так: <code>@app.get(\"/health\")</code>.",
            "Верните из функции словарь: Flask сам превратит его в JSON.",
        ]},
        "solution": "from flask import Flask\n\napp = Flask(__name__)\n\n@app.get(\"/health\")\ndef health():\n    return {\"status\": \"ok\"}",
        "tests": "client = app.test_client()\ncase('client.get(\"/health\").status_code', 200)\ncase('client.get(\"/health\").json', {\"status\": \"ok\"})\ncase('client.post(\"/health\").status_code', 405)",
    },
    "square": {
        "level": "easy",
        "title": {"ru": "Число в адресе"},
        "text": {"ru": "Сделайте <code>GET /square/&lt;int:n&gt;</code>: верните JSON с числом и его квадратом, например <code>{\"n\": 4, \"square\": 16}</code>. Адрес <code>/square/abc</code> должен давать 404."},
        "starter": "from flask import Flask\n\napp = Flask(__name__)\n\n# ваш маршрут",
        "hints": {"ru": [
            "<code>&lt;int:n&gt;</code> в адресе пропускает только числа и передаёт в функцию уже число, а не строку.",
            "Функция должна принимать аргумент с тем же именем: <code>def square(n):</code>.",
        ]},
        "solution": "from flask import Flask\n\napp = Flask(__name__)\n\n@app.get(\"/square/<int:n>\")\ndef square(n):\n    return {\"n\": n, \"square\": n * n}",
        "tests": "client = app.test_client()\ncase('client.get(\"/square/4\").json', {\"n\": 4, \"square\": 16})\ncase('client.get(\"/square/0\").json', {\"n\": 0, \"square\": 0})\ncase('client.get(\"/square/abc\").status_code', 404)",
    },
    "search_q": {
        "level": "medium",
        "title": {"ru": "Обязательный параметр"},
        "text": {"ru": "Сделайте <code>GET /search</code>. Если в адресе есть непустой параметр <code>q</code>, верните <code>{\"q\": значение}</code>. Если параметра нет или он из одних пробелов, верните <code>{\"error\": \"q\"}</code> с кодом 400."},
        "starter": "from flask import Flask, request\n\napp = Flask(__name__)\n\n# ваш маршрут",
        "hints": {"ru": [
            "Параметр читает <code>request.args.get(\"q\", \"\")</code>: второе значение вернётся, если параметра нет.",
            "Код ответа ставится вторым значением: <code>return {\"error\": \"q\"}, 400</code>.",
        ]},
        "solution": "from flask import Flask, request\n\napp = Flask(__name__)\n\n@app.get(\"/search\")\ndef search():\n    q = request.args.get(\"q\", \"\").strip()\n    if not q:\n        return {\"error\": \"q\"}, 400\n    return {\"q\": q}",
        "tests": "client = app.test_client()\ncase('client.get(\"/search?q=flask\").json', {\"q\": \"flask\"})\ncase('client.get(\"/search\").status_code', 400)\ncase('client.get(\"/search\").json', {\"error\": \"q\"})\ncase('client.get(\"/search?q=%20\").status_code', 400)",
    },
    "remove": {
        "level": "hard",
        "title": {"ru": "Удаление по номеру"},
        "text": {"ru": "Сделайте <code>DELETE /tasks/&lt;int:task_id&gt;</code>. Если задача есть в словаре <code>TASKS</code>, удалите её и верните пустой ответ с кодом 204. Если её нет, верните <code>{\"error\": \"not found\"}</code> с кодом 404."},
        "starter": "from flask import Flask\n\napp = Flask(__name__)\nTASKS = {1: \"Buy bread\", 2: \"Learn Flask\"}\n\n# ваш маршрут",
        "hints": {"ru": [
            "Маршрут для удаления объявляют через <code>@app.delete(...)</code>. Из словаря элемент убирает <code>del TASKS[task_id]</code>.",
            "Пустой ответ с кодом: <code>return \"\", 204</code>.",
        ]},
        "solution": "from flask import Flask\n\napp = Flask(__name__)\nTASKS = {1: \"Buy bread\", 2: \"Learn Flask\"}\n\n@app.delete(\"/tasks/<int:task_id>\")\ndef delete_task(task_id):\n    if task_id not in TASKS:\n        return {\"error\": \"not found\"}, 404\n    del TASKS[task_id]\n    return \"\", 204",
        "tests": "client = app.test_client()\ncase('client.delete(\"/tasks/1\").status_code', 204)\ncase('TASKS', {2: \"Learn Flask\"})\ncase('client.delete(\"/tasks/1\").status_code', 404)\ncase('client.delete(\"/tasks/9\").json', {\"error\": \"not found\"})\ncase('client.get(\"/tasks/2\").status_code', 405)",
    },
}


def pick(value, lang):
    if isinstance(value, dict):
        return value.get(lang) or value["ru"]
    return value


# Переводы задач: tools/i18n/practice.json, {язык: {"tasks": {задача: {title, text, hints}}, "code": [[ru, перевод], ...]}}.
# "code" — замены строк в коде и тестах (приветствия, примеры данных, подсказки проверок); имена в коде не меняются.
PRACTICE_TR_PATH = ROOT / "tools" / "i18n" / "practice.json"
PRACTICE_TR = json.loads(PRACTICE_TR_PATH.read_text(encoding="utf-8")) if PRACTICE_TR_PATH.exists() else {}


def text_of(slug, field, lang):
    translated = PRACTICE_TR.get(lang, {}).get("tasks", {}).get(slug, {}).get(field)
    return translated if translated else pick(TASKS[slug][field], lang)


def code_of(slug, field, lang):
    code = pick(TASKS[slug][field], lang)
    for ru, tr in PRACTICE_TR.get(lang, {}).get("code", []):
        code = code.replace(ru, tr)
    return code


def esc(code):
    return html.escape(code, quote=False)


def task_html(slug, number, lang):
    task = TASKS[slug]
    title = f"{number}. {text_of(slug, 'title', lang)}"
    level = task["level"]
    hints = text_of(slug, "hints", lang)
    rows = max(5, code_of(slug, "starter", lang).count("\n") + 3)
    hint_items = "\n".join(f'<li hidden tabindex="-1"><strong>{pick(UI["hint"], lang)} {i}.</strong> {h}</li>' for i, h in enumerate(hints, 1))
    return f'''<article class="task reveal" data-task="{slug}" data-level="{level}">
<div class="task-head"><h3>{title}</h3><span class="level level-{level}"><span class="visually-hidden">{pick(UI["level"], lang)}: </span>{LEVELS[level][lang]}</span></div>
<p>{text_of(slug, "text", lang)}</p>
<textarea class="editor-area" rows="{rows}" spellcheck="false" aria-label="{pick(UI["answer"], lang)}: {html.escape(title)}">{esc(code_of(slug, "starter", lang))}</textarea>
<div class="tool-row"><button class="btn btn-primary" type="button" data-check>{pick(UI["check"], lang)}</button><button class="btn btn-secondary" type="button" data-reset>{pick(UI["reset"], lang)}</button></div>
<div data-output></div>
<div class="hints" data-hints>
<button class="btn btn-secondary hint-next" type="button" data-hint-next>{pick(UI["hint"], lang)} 1 / {len(hints)}</button>
<ol class="hint-list" aria-label="{pick(UI["hints"], lang)}" aria-live="polite">
{hint_items}
</ol>
</div>
<details class="solution"><summary>{pick(UI["solution"], lang)}</summary><pre><code>{esc(code_of(slug, "solution", lang))}</code></pre></details>
<template data-kind="tests">{esc(code_of(slug, "tests", lang))}</template>
</article>'''


def build(lang):
    out = []
    number = 0
    for section in SECTIONS:
        articles = []
        for slug in section["tasks"]:
            number += 1
            articles.append(task_html(slug, number, lang))
        out.append(f'''<section class="section" id="{section["id"]}" aria-labelledby="{section["id"]}-title">
<div class="container">
<div class="section-head reveal">
<h2 id="{section["id"]}-title">{pick(section["title"], lang)}</h2>
<p>{pick(section["lead"], lang)}</p>
</div>
''' + "\n".join(articles) + "\n</div>\n</section>")
    return "\n".join(out)


def total():
    return sum(len(section["tasks"]) for section in SECTIONS)


def main():
    check = "--check" in sys.argv
    stale = []

    def update(path, new):
        if path.read_text(encoding="utf-8") != new:
            stale.append(path.relative_to(ROOT).as_posix())
            if not check:
                path.write_text(new, encoding="utf-8", newline="\n")

    for lang, path in (("ru", ROOT / "practice.html"), ("kk", ROOT / "kk" / "practice.html"), ("en", ROOT / "en" / "practice.html")):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "<!-- tasks:start -->" not in text:
            sys.exit(f"{path}: нет метки <!-- tasks:start -->")
        new = re.sub(r"<!-- tasks:start -->.*?<!-- tasks:end -->",
                     lambda m: "<!-- tasks:start -->\n" + build(lang) + "\n<!-- tasks:end -->", text, flags=re.S)
        # Число стоит и в атрибуте, и в тексте: без JavaScript и для поиска оно должно быть верным
        new = re.sub(r'data-tasks-total="\d+">\d*<', f'data-tasks-total="{total()}">{total()}<', new)
        update(path, new)
    course = ROOT / "course.html"
    update(course, re.sub(r'data-tasks="\d+"', f'data-tasks="{total()}"', course.read_text(encoding="utf-8")))
    if check:
        if stale:
            print("Задачи на страницах отличаются от tools/build_practice.py. Запустите python tools/build_practice.py:")
            print("\n".join("  " + s for s in stale))
            sys.exit(1)
        print("Задачи на страницах актуальны")
        return
    print(f"Задач: {total()}, обновлено файлов: {len(stale)}")


if __name__ == "__main__":
    main()
