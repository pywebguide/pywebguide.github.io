from flask import Flask, redirect, render_template_string, request, url_for

app = Flask(__name__)
tasks = []

PAGE = """
<!doctype html>
<title>Мои задачи</title>
<h1>Мои задачи</h1>
<form method="post">
  <input name="title" placeholder="Новая задача" required>
  <button>Добавить</button>
</form>
<ul>
  {% for task in tasks %}<li>{{ task }}</li>{% endfor %}
</ul>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if title:
            tasks.append(title)
        return redirect(url_for("index"))
    return render_template_string(PAGE, tasks=tasks)
