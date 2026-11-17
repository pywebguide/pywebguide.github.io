from itertools import count

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="Список задач")

class TaskCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)

class Task(BaseModel):
    id: int
    title: str
    done: bool = False

tasks: dict[int, Task] = {}
ids = count(1)

def find(task_id: int) -> Task:
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return tasks[task_id]

@app.get("/tasks")
def list_tasks() -> list[Task]:
    return list(tasks.values())

@app.post("/tasks", status_code=201)
def create_task(data: TaskCreate) -> Task:
    task = Task(id=next(ids), title=data.title)
    tasks[task.id] = task
    return task

@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> Task:
    return find(task_id)

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int) -> None:
    del tasks[find(task_id).id]
