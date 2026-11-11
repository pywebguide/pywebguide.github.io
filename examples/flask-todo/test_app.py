"""Проверка примера: python -m pytest или python test_app.py"""
import tempfile
import unittest
from pathlib import Path

import app as todo


class TodoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        todo.DB = Path(self.tmp.name) / "tasks.db"
        todo.query("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")
        self.client = todo.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_and_delete(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.client.post("/add", data={"title": "Купить хлеб"})
        self.assertIn("Купить хлеб", self.client.get("/").get_data(as_text=True))
        self.client.post("/delete/1")
        self.assertNotIn("Купить хлеб", self.client.get("/").get_data(as_text=True))

    def test_empty_title_is_not_saved(self):
        self.client.post("/add", data={"title": "   "})
        self.client.post("/add", data={})
        self.assertEqual(todo.query("SELECT COUNT(*) FROM tasks")[0][0], 0)

    def test_delete_needs_post(self):
        self.assertEqual(self.client.get("/delete/1").status_code, 405)


if __name__ == "__main__":
    unittest.main()
