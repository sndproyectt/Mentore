from django.contrib import admin
from .models import StudentWork, WorkCategory

@admin.register(StudentWork)
class StudentWorkAdmin(admin.ModelAdmin):
    list_display = ['title', 'student', 'teacher', 'is_public', 'created_at']
    list_filter = ['is_public', 'category']

@admin.register(WorkCategory)
class WorkCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'teacher']
