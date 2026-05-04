from django.contrib import admin
from .models import Student, Classroom

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'classroom', 'teacher', 'active', 'created_at']
    list_filter = ['active', 'classroom', 'gender']
    search_fields = ['first_name', 'last_name', 'document_id']

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ['name', 'grade_level', 'subject', 'teacher']
