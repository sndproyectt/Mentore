from django.contrib import admin
from django.utils.html import format_html
from .models import TeacherProfile


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'role', 'subject', 'school_name', 'city', 'assigned_subjects']
    list_filter   = ['role', 'is_homeroom_teacher']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'subject', 'school_name']
    list_editable = ['role']
    readonly_fields = ['created_at']

    def assigned_subjects(self, obj):
        from grades.models import TeacherSubject
        subjects = TeacherSubject.objects.filter(
            teacher=obj.user
        ).select_related('subject').values_list('subject__name', flat=True)
        if subjects:
            badges = ' '.join(
                f'<span style="background:#E8F5FD;color:#1570A6;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">{s}</span>'
                for s in subjects
            )
            return format_html(badges)
        return '—'
    assigned_subjects.short_description = 'Materias asignadas'
    assigned_subjects.allow_tags = True
