from django.contrib import admin
from django.urls import path

from tasks import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("tasks/<int:pk>/toggle/", views.toggle, name="toggle"),
    path("tasks/<int:pk>/delete/", views.delete, name="delete"),
]
