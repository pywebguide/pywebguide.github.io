from django.test import TestCase
from django.urls import reverse

from .models import Category, Task

class TaskViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.study = Category.objects.create(name="Учёба")
        cls.home = Category.objects.create(name="Дом")
        Task.objects.create(title="Сдать лабораторную", category=cls.study)
        Task.objects.create(title="Вынести мусор", category=cls.home)
        Task.objects.create(title="Без категории")

    def test_list_shows_all_tasks(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/index.html")
        self.assertEqual(len(response.context["tasks"]), 3)

    def test_category_shows_only_its_tasks(self):
        response = self.client.get(reverse("category", args=[self.study.pk]))
        self.assertContains(response, "Сдать лабораторную")
        self.assertNotContains(response, "Вынести мусор")

    def test_unknown_category_is_404(self):
        response = self.client.get(reverse("category", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_create_saves_task_and_redirects(self):
        response = self.client.post(reverse("add"), {"title": "Полить цветы", "category": self.home.pk})
        self.assertRedirects(response, reverse("index"))
        self.assertTrue(self.home.tasks.filter(title="Полить цветы").exists())

    def test_create_rejects_empty_title(self):
        response = self.client.post(reverse("add"), {"title": ""})
        self.assertEqual(response.status_code, 200)
        self.assertIn("title", response.context["form"].errors)
        self.assertEqual(Task.objects.count(), 3)

    def test_list_needs_same_queries_for_any_number_of_tasks(self):
        for number in range(10):
            Task.objects.create(title=f"Задача {number}", category=self.study)
        with self.assertNumQueries(3):
            self.client.get(reverse("index"))
