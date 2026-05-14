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

    # Estudiantes (acceso total)
    path('students/',                                        views.student_list,            name='student_list'),
    path('students/<int:pk>/',                               views.student_detail,          name='student_detail'),
    path('students/<int:pk>/edit/',                          views.student_edit,            name='student_edit'),
    path('students/<int:student_pk>/message/',               views.student_message_send,    name='student_message'),
    # Padres de familia
    path('parents/',                                         views.parent_message_list,     name='parent_message_list'),
    path('parents/message/',                                 views.parent_message_create,   name='parent_message_create'),
    # Materias
    path('subjects/',                               views.subject_list,      name='subject_list'),
    path('subjects/new/',                           views.subject_create,    name='subject_create'),
    path('subjects/<int:subject_id>/assign/',       views.subject_assign,    name='subject_assign'),
    path('teachers/<int:teacher_id>/subjects/',     views.teacher_subjects,  name='teacher_subjects'),
]