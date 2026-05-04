from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('students/', views.student_list, name='list'),
    path('students/new/', views.student_create, name='create'),
    path('students/<int:pk>/', views.student_detail, name='detail'),
    path('students/<int:pk>/edit/', views.student_edit, name='edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='delete'),
    path('classrooms/', views.classroom_list, name='classrooms'),
    path('classrooms/new/', views.classroom_create, name='classroom_create'),
    # Announcements
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/new/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),
    # Attendance
    path('attendance/', views.attendance_view, name='attendance'),
    path('attendance/save/', views.save_attendance, name='save_attendance'),
    # Schedule
    path('schedule/', views.schedule_view, name='schedule'),
    # Messaging
    path('messages/', views.message_list, name='message_list'),
    path('messages/new/', views.message_create, name='message_create'),
    path('messages/<int:pk>/delete/', views.message_delete, name='message_delete'),
]
