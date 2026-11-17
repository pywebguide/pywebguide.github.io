from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView

from .forms import TaskForm
from .models import Category, Task

class TaskListView(ListView):
    template_name = "tasks/index.html"
    context_object_name = "tasks"

    def get_queryset(self):
        self.current = None
        if "pk" in self.kwargs:
            self.current = get_object_or_404(Category, pk=self.kwargs["pk"])
            return self.current.tasks.all()
        return Task.objects.select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        context["current"] = self.current
        context["form"] = TaskForm(initial={"category": self.current})
        return context

class TaskCreateView(CreateView):
    model = Task
    form_class = TaskForm
    success_url = reverse_lazy("index")

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
