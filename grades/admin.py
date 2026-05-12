from django.contrib import admin
from django.db.models import Avg
from .models import Grade, Subject, TeacherSubject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'active', 'teacher_count', 'grade_count']
    list_filter   = ['active']
    search_fields = ['name', 'code']
    list_editable = ['active']

    def teacher_count(self, obj):
        return obj.teacher_assignments.count()
    teacher_count.short_description = 'Docentes'

    def grade_count(self, obj):
        return obj.grades.count()
    grade_count.short_description = 'Notas'


@admin.register(TeacherSubject)
class TeacherSubjectAdmin(admin.ModelAdmin):
    list_display  = ['teacher', 'subject', 'assigned_at']
    list_filter   = ['subject']
    search_fields = ['teacher__first_name', 'teacher__last_name', 'subject__name']
    autocomplete_fields = ['subject']


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display  = ['student', 'subject', 'subject_text', 'activity_name',
                     'grade_type', 'score', 'period', 'date']
    list_filter   = ['subject', 'grade_type', 'period']
    search_fields = ['student__first_name', 'student__last_name',
                     'activity_name', 'subject__name', 'subject_text']
    list_select_related = ['student', 'subject']
    date_hierarchy = 'date'
    ordering = ['-date']
