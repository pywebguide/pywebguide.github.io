from django.test import TestCase
from django.urls import reverse

from .models import Task


class TaskPageTests(TestCase):
    def test_empty_list(self):
        response = self.client.get("/")
        self.assertContains(response, "Задач пока нет.")

    def test_add_toggle_delete(self):
        self.client.post("/", {"title": "Купить хлеб"})
        task = Task.objects.get()
        self.assertContains(self.client.get("/"), "Купить хлеб")

        self.client.post(reverse("toggle", args=[task.pk]))
        task.refresh_from_db()
        self.assertTrue(task.done)
        self.assertContains(self.client.get("/"), "<s>Купить хлеб</s>", html=True)

        self.client.post(reverse("delete", args=[task.pk]))
        self.assertFalse(Task.objects.exists())

    def test_empty_title_is_rejected(self):
        response = self.client.post("/", {"title": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.exists())

    def test_delete_needs_post(self):
        task = Task.objects.create(title="Не удалять")
        response = self.client.get(reverse("delete", args=[task.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Task.objects.exists())
