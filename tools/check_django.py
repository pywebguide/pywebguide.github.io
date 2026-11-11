"""Проверка примеров Django: проект собирается из кода со страниц сайта, затем запускаются тесты и сверяется вывод sqlmigrate.
Код выхода 1 при ошибках. Нужен Django из tools/requirements.txt."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from codeblocks import read

ROOT = Path(__file__).resolve().parent.parent
W = Path()
PY = sys.executable


def blocks(page):
    return [(b["label"].strip(), b["code"]) for b in read(ROOT / page)]


def last(page, label):
    found = [code for lab, code in blocks(page) if lab == label]
    assert found, (page, label, [lab for lab, _ in blocks(page)])
    return found[-1]


def run(*args, ok=True):
    result = subprocess.run([PY, *args], cwd=W, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if ok and result.returncode:
        print("ОШИБКА", args, "\n", result.stdout[-1500:], result.stderr[-1500:])
        sys.exit(1)
    return result


EXTRA_TESTS = '''

from django.contrib.auth.models import User
from django.test import Client
import json


class SiteClaims(TestCase):
    """Утверждения из текста сайта, проверенные на настоящем Django."""

    def test_step10_empty_task_shows_error_and_saves_nothing(self):
        response = self.client.post(reverse("index"), {"title": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "errorlist")
        self.assertEqual(Task.objects.count(), 0)

    def test_step10_toggle_strikes_and_delete_removes(self):
        task = Task.objects.create(title="Купить хлеб")
        self.assertRedirects(self.client.post(reverse("toggle", args=[task.pk])), reverse("index"))
        task.refresh_from_db()
        self.assertTrue(task.done)
        self.assertContains(self.client.get(reverse("index")), "<s>Купить хлеб</s>", html=True)
        self.assertRedirects(self.client.post(reverse("delete", args=[task.pk])), reverse("index"))
        self.assertEqual(Task.objects.count(), 0)

    def test_require_post_blocks_plain_link(self):
        task = Task.objects.create(title="x")
        self.assertEqual(self.client.get(reverse("delete", args=[task.pk])).status_code, 405)

    def test_form_without_csrf_token_gets_403(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("index"), {"title": "x"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF verification failed", response.content.decode())

    def test_template_contains_csrf_token(self):
        page = Client(enforce_csrf_checks=True).get(reverse("index")).content.decode()
        self.assertIn("csrfmiddlewaretoken", page)

    def test_login_required_redirects_to_login(self):
        self.assertRedirects(self.client.get("/profile/"), "/accounts/login/?next=/profile/", fetch_redirect_response=False)

    def test_logout_works_only_by_post(self):
        self.assertEqual(self.client.get("/accounts/logout/").status_code, 405)
        User.objects.create_user("aru", password="секрет12345")
        self.client.login(username="aru", password="секрет12345")
        self.assertContains(self.client.get("/profile/"), "Профиль aru")
        self.assertRedirects(self.client.post("/accounts/logout/"), "/accounts/login/", fetch_redirect_response=False)

    def test_json_api(self):
        post = lambda body: self.client.post("/api/tasks/", body, content_type="application/json")
        self.assertEqual(post("{}").status_code, 400)
        self.assertEqual(post("не json").status_code, 400)
        self.assertEqual(post("[1]").status_code, 400)
        created = post(json.dumps({"title": "API"}))
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.get("/api/tasks/").json(), [{"id": created.json()["id"], "title": "API"}])
        self.assertEqual(self.client.delete("/api/tasks/").status_code, 405)

    def test_order_by_hint_puts_unfinished_first(self):
        Task.objects.create(title="a", done=True)
        fresh = Task.objects.create(title="b")
        self.assertEqual(list(Task.objects.order_by("done", "-id"))[0], fresh)
'''


def build():
    subprocess.run([PY, "-m", "django", "startproject", "mysite", "."], cwd=W, check=True)
    run("manage.py", "startapp", "tasks")
    run("manage.py", "startapp", "shop")

    settings = W / "mysite" / "settings.py"
    text = settings.read_text(encoding="utf-8")
    site_apps = last("project.html", "mysite/settings.py")
    text = re.sub(r"INSTALLED_APPS = \[.*?\]\n", lambda m: site_apps.replace("'tasks',\n", "'tasks',\n    'shop',\n") + "\n", text, flags=re.S)
    text += "\n" + last("auth.html", "mysite/settings.py") + "\n"
    settings.write_text(text, encoding="utf-8")

    app = W / "tasks"
    (app / "models.py").write_text(last("project.html", "tasks/models.py"), encoding="utf-8")
    (app / "admin.py").write_text(last("project.html", "tasks/admin.py"), encoding="utf-8")
    (app / "forms.py").write_text(last("project.html", "tasks/forms.py"), encoding="utf-8")
    (app / "views.py").write_text(last("project.html", "tasks/views.py"), encoding="utf-8")
    (app / "auth_views.py").write_text(last("auth.html", "tasks/views.py"), encoding="utf-8")
    (app / "api.py").write_text(last("api.html", "tasks/views.py"), encoding="utf-8")
    templates = app / "templates"
    (templates / "tasks").mkdir(parents=True)
    (templates / "tasks" / "index.html").write_text(last("project.html", "tasks/templates/tasks/index.html"), encoding="utf-8")
    (templates / "profile.html").write_text("Профиль {{ user.username }}", encoding="utf-8")
    (templates / "registration").mkdir()
    (templates / "registration" / "login.html").write_text('<form method="post">{% csrf_token %}{{ form.as_p }}</form>', encoding="utf-8")

    urls = last("project.html", "mysite/urls.py")
    assert 'include("django.contrib.auth.urls")' in last("auth.html", "mysite/urls.py")
    urls = urls.replace("from django.urls import path", "from django.urls import include, path\nfrom tasks import api, auth_views")
    extra_routes = '    path("accounts/", include("django.contrib.auth.urls")),\n    path("profile/", auth_views.profile, name="profile"),\n    path("api/tasks/", api.tasks),\n]'
    urls = urls.rstrip().removesuffix("]") + extra_routes + "\n"
    (W / "mysite" / "urls.py").write_text(urls, encoding="utf-8")

    (app / "tests.py").write_text(last("testing.html", "tasks/tests.py") + EXTRA_TESTS, encoding="utf-8")
    (W / "shop" / "models.py").write_text(last("databases.html", "shop/models.py"), encoding="utf-8")

    print("check:", run("manage.py", "check").stdout.strip())
    print(run("manage.py", "makemigrations").stdout.strip())
    print("migrate:", run("manage.py", "migrate").stdout.strip().splitlines()[-1])

    sql = run("manage.py", "sqlmigrate", "shop", "0001").stdout
    site_sql = last("databases.html", "SQL, который сгенерировал Django")
    # Сравниваем без комментариев и пробелов: Django и сайт расставляют переносы по-разному
    norm = lambda value: re.sub(r"\s+", "", re.sub(r"--[^\n]*", "", value))
    create = [part for part in sql.split(";") if "CREATE TABLE" in part][0]
    sql_ok = norm(create) + ";" == norm(site_sql)
    print("sqlmigrate совпадает с сайтом:", sql_ok)
    if not sql_ok:
        print("ОШИБКА: на сайте другой SQL. Django выдал:\n" + create.strip() + ";")

    shell = last("databases.html", "python manage.py shell")
    probe = shell + '\nprint("осталось =", list(Product.objects.values_list("name", "price")))'
    print("shell:", run("manage.py", "shell", "-c", probe).stdout.strip())

    result = run("manage.py", "test", "tasks", "-v", "2", ok=False)
    keep = (" ... ", "Ran", "OK", "FAILED", "FAIL:", "ERROR:", "AssertionError", "Traceback", "  File")
    print("\n".join(line for line in result.stderr.splitlines() if line.startswith(keep) or " ... " in line))
    return 1 if result.returncode or not sql_ok else 0


def main():
    global W
    with tempfile.TemporaryDirectory() as folder:
        W = Path(folder)
        return build()


if __name__ == "__main__":
    sys.exit(main())
