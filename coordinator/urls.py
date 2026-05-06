from django.urls import path
from . import views

app_name = 'coordinator'

urlpatterns = [
    # Dashboard
    path('',                                        views.coordinator_dashboard, name='dashboard'),

    # Salones
    path('classrooms/',                             views.classroom_list,        name='classroom_list'),
    path('classrooms/new/',                         views.classroom_create,      name='classroom_create'),
    path('classrooms/<int:classroom_id>/assign/',   views.classroom_assign,      name='classroom_assign'),
    path('classrooms/<int:classroom_id>/delete/',   views.classroom_delete,      name='classroom_delete'),

    # Profesores
    path('teachers/',                               views.teacher_list,          name='teacher_list'),
    path('teachers/new/',                           views.teacher_create,        name='teacher_create'),
    path('teachers/<int:teacher_id>/',              views.teacher_detail,        name='teacher_detail'),
    path('teachers/<int:teacher_id>/role/',         views.teacher_change_role,   name='teacher_change_role'),

    # Comunicados
    path('announcements/',                          views.announcement_list,     name='announcement_list'),
    path('announcements/new/',                      views.announcement_create,   name='announcement_create'),
    path('announcements/<int:pk>/delete/',          views.announcement_delete,   name='announcement_delete'),

    # Estudiantes (vista global)
    path('students/',                               views.student_list,          name='student_list'),
]
