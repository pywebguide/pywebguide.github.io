import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)

@pytest.fixture(autouse=True)
def empty_list():
    main.tasks.clear()

def test_create_and_list():
    response = client.post("/tasks", json={"title": "Купить хлеб"})
    assert response.status_code == 201
    task = response.json()
    assert task["title"] == "Купить хлеб"
    assert task["done"] is False
    assert client.get("/tasks").json() == [task]

def test_empty_title_is_rejected():
    response = client.post("/tasks", json={"title": "   "})
    assert response.status_code == 422
    assert client.get("/tasks").json() == []

def test_missing_task_is_404():
    response = client.get("/tasks/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Задача не найдена"}

def test_delete():
    task_id = client.post("/tasks", json={"title": "Удалить меня"}).json()["id"]
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404

def test_id_must_be_a_number():
    assert client.get("/tasks/abc").status_code == 422
