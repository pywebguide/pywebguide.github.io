from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import TaskForm
from .models import Task

def index(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("index")
    else:
        form = TaskForm()
    return render(request, "tasks/index.html", {"tasks": Task.objects.all(), "form": form})

@require_POST
def toggle(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.done = not task.done
    task.save()
    return redirect("index")

@require_POST
def delete(request, pk):
    get_object_or_404(Task, pk=pk).delete()
    return redirect("index")
