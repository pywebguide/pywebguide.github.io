import sqlite3
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for

app = Flask(__name__)
DB = Path(__file__).with_name("tasks.db")

PAGE = """
<!doctype html>
<title>Мои задачи</title>
<h1>Мои задачи</h1>
<form method="post" action="{{ url_for('add') }}">
  <input name="title" placeholder="Новая задача" required>
  <button>Добавить</button>
</form>
<ul>
  {% for task in tasks %}
    <li>
      {{ task["title"] }}
      <form method="post" action="{{ url_for('delete', task_id=task['id']) }}">
        <button>Удалить</button>
      </form>
    </li>
  {% endfor %}
</ul>
"""

def query(sql, params=()):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()

query("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")

@app.get("/")
def index():
    tasks = query("SELECT id, title FROM tasks ORDER BY id")
    return render_template_string(PAGE, tasks=tasks)

@app.post("/add")
def add():
    title = request.form.get("title", "").strip()
    if title:
        query("INSERT INTO tasks (title) VALUES (?)", (title,))
    return redirect(url_for("index"))

@app.post("/delete/<int:task_id>")
def delete(task_id):
    query("DELETE FROM tasks WHERE id = ?", (task_id,))
    return redirect(url_for("index"))
