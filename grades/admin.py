from django.contrib import admin
from .models import Grade

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['student', 'activity_name', 'grade_type', 'score', 'date']
    list_filter = ['grade_type', 'period']
    search_fields = ['student__first_name', 'student__last_name', 'activity_name']
