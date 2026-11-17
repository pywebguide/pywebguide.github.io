from django.contrib import admin

from .models import Category, Task

admin.site.register(Category)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "done"]
    list_filter = ["category", "done"]
