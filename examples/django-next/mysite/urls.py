from django.contrib import admin
from django.urls import path

from tasks import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.TaskListView.as_view(), name="index"),
    path("category/<int:pk>/", views.TaskListView.as_view(), name="category"),
    path("tasks/add/", views.TaskCreateView.as_view(), name="add"),
    path("tasks/<int:pk>/toggle/", views.toggle, name="toggle"),
    path("tasks/<int:pk>/delete/", views.delete, name="delete"),
]
