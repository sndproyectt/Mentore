from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import date, timedelta
from .models import Student, Classroom, Announcement, Attendance, Message
from grades.models import Grade


@login_required
def dashboard(request):
    students = Student.objects.filter(teacher=request.user, active=True)
    classrooms = Classroom.objects.filter(teacher=request.user)
    total_grades = Grade.objects.filter(student__teacher=request.user)
    avg = total_grades.aggregate(Avg('score'))['score__avg'] or 0
    recent_students = students.order_by('-created_at')[:5]
    announcements = Announcement.objects.filter(teacher=request.user).order_by('-created_at')[:3]
    # Attendance today
    today = date.today()
    present_today = Attendance.objects.filter(student__teacher=request.user, date=today, status='present').count()
    absent_today  = Attendance.objects.filter(student__teacher=request.user, date=today, status='absent').count()
    context = {
        'total_students': students.count(),
        'total_classrooms': classrooms.count(),
        'total_grades': total_grades.count(),
        'avg_grade': round(avg, 1),
        'recent_students': recent_students,
        'classrooms': classrooms,
        'announcements': announcements,
        'present_today': present_today,
        'absent_today': absent_today,
    }
    return render(request, 'students/dashboard.html', context)


@login_required
def student_list(request):
    query = request.GET.get('q', '')
    classroom_id = request.GET.get('classroom', '')
    students = Student.objects.filter(teacher=request.user, active=True)
    if query:
        students = students.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(document_id__icontains=query)
        )
    if classroom_id:
        students = students.filter(classroom_id=classroom_id)
    classrooms = Classroom.objects.filter(teacher=request.user)
    return render(request, 'students/student_list.html', {
        'students': students, 'classrooms': classrooms,
        'query': query, 'selected_classroom': classroom_id,
    })


@login_required
def student_create(request):
    classrooms = Classroom.objects.filter(teacher=request.user)
    if request.method == 'POST':
        p = request.POST
        student = Student.objects.create(
            teacher=request.user,
            first_name=p.get('first_name', ''), last_name=p.get('last_name', ''),
            document_id=p.get('document_id', ''), email=p.get('email', ''),
            parent_email=p.get('parent_email', '').strip().lower(), parent_name=p.get('parent_name', ''),
            parent_phone=p.get('parent_phone', ''), gender=p.get('gender', ''),
            notes=p.get('notes', ''), classroom_id=p.get('classroom') or None,
        )
        if 'photo' in request.FILES:
            student.photo = request.FILES['photo']
            student.save()
        messages.success(request, f'Estudiante {student.get_full_name()} creado exitosamente.')
        return redirect('students:list')
    return render(request, 'students/student_form.html', {'classrooms': classrooms, 'action': 'Crear'})


@login_required
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk, teacher=request.user)
    classrooms = Classroom.objects.filter(teacher=request.user)
    if request.method == 'POST':
        p = request.POST
        student.first_name = p.get('first_name', student.first_name)
        student.last_name = p.get('last_name', student.last_name)
        student.document_id = p.get('document_id', student.document_id)
        student.email = p.get('email', student.email).strip().lower()
        student.parent_email = p.get('parent_email', student.parent_email).strip().lower()
        student.parent_name = p.get('parent_name', student.parent_name)
        student.parent_phone = p.get('parent_phone', student.parent_phone)
        student.gender = p.get('gender', student.gender)
        student.notes = p.get('notes', student.notes)
        student.classroom_id = p.get('classroom') or None
        if 'photo' in request.FILES:
            student.photo = request.FILES['photo']
        student.save()
        messages.success(request, 'Estudiante actualizado correctamente.')
        return redirect('students:list')
    return render(request, 'students/student_form.html', {
        'student': student, 'classrooms': classrooms, 'action': 'Editar'
    })


@login_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk, teacher=request.user)
    if request.method == 'POST':
        name = student.get_full_name()
        student.active = False
        student.save()
        messages.success(request, f'Estudiante {name} eliminado.')
    return redirect('students:list')


@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk, teacher=request.user)
    grades = student.grades.order_by('-date')
    all_attendances = student.attendances.order_by('-date')
    present = all_attendances.filter(status='P').count()
    absent  = all_attendances.filter(status='A').count()
    attendances = all_attendances[:30]
    messages_sent = student.messages.order_by('-sent_at')[:10]
    return render(request, 'students/student_detail.html', {
        'student': student, 'grades': grades,
        'attendances': attendances, 'present': present, 'absent': absent,
        'messages_sent': messages_sent,
        'student_data': [],
    })


@login_required
def classroom_list(request):
    classrooms = Classroom.objects.filter(teacher=request.user)
    return render(request, 'students/classroom_list.html', {'classrooms': classrooms})


@login_required
def classroom_create(request):
    if request.method == 'POST':
        p = request.POST
        Classroom.objects.create(
            teacher=request.user, name=p.get('name', ''),
            grade_level=p.get('grade_level', ''), subject=p.get('subject', ''),
        )
        messages.success(request, 'Grupo creado exitosamente.')
        return redirect('students:classrooms')
    return render(request, 'students/classroom_form.html', {'action': 'Crear'})


# ── ANNOUNCEMENTS ────────────────────────────────────────────
@login_required
def announcement_list(request):
    announcements = Announcement.objects.filter(teacher=request.user)
    classrooms = Classroom.objects.filter(teacher=request.user)
    return render(request, 'students/announcement_list.html', {
        'announcements': announcements, 'classrooms': classrooms
    })


@login_required
def announcement_create(request):
    classrooms = Classroom.objects.filter(teacher=request.user)
    if request.method == 'POST':
        p = request.POST
        Announcement.objects.create(
            teacher=request.user,
            title=p.get('title', ''),
            content=p.get('content', ''),
            priority=p.get('priority', 'low'),
            classroom_id=p.get('classroom') or None,
        )
        messages.success(request, 'Comunicado creado correctamente.')
        return redirect('students:announcement_list')
    return render(request, 'students/announcement_form.html', {'classrooms': classrooms})


@login_required
def announcement_delete(request, pk):
    ann = get_object_or_404(Announcement, pk=pk, teacher=request.user)
    if request.method == 'POST':
        ann.delete()
        messages.success(request, 'Comunicado eliminado.')
    return redirect('students:announcement_list')


# ── ATTENDANCE ────────────────────────────────────────────────
@login_required
def attendance_view(request):
    classroom_id = request.GET.get('classroom', '')
    selected_date = request.GET.get('date', date.today().isoformat())
    classrooms = Classroom.objects.filter(teacher=request.user)
    students = []
    attendance_map = {}

    if classroom_id:
        students = Student.objects.filter(teacher=request.user, classroom_id=classroom_id, active=True)
        records = Attendance.objects.filter(student__in=students, date=selected_date)
        attendance_map = {r.student_id: r for r in records}

    return render(request, 'students/attendance.html', {
        'classrooms': classrooms, 'students': students,
        'selected_classroom': classroom_id, 'selected_date': selected_date,
        'attendance_map': attendance_map,
        'status_choices': Attendance.STATUS_CHOICES,
    })


@login_required
@require_POST
def save_attendance(request):
    classroom_id = request.POST.get('classroom_id')
    selected_date = request.POST.get('date', date.today().isoformat())
    students = Student.objects.filter(teacher=request.user, classroom_id=classroom_id, active=True)
    for student in students:
        status = request.POST.get(f'status_{student.pk}', 'present')
        note   = request.POST.get(f'note_{student.pk}', '')
        Attendance.objects.update_or_create(
            student=student, date=selected_date,
            defaults={'status': status, 'note': note}
        )
    messages.success(request, f'Asistencia guardada para {selected_date}.')
    return redirect(f"/dashboard/attendance/?classroom={classroom_id}&date={selected_date}")


# ── SCHEDULE ────────────────────────────────────────────────
@login_required
def schedule_view(request):
    classrooms = Classroom.objects.filter(teacher=request.user)
    return render(request, 'students/schedule.html', {'classrooms': classrooms})


# ── MESSAGING ────────────────────────────────────────────────
@login_required
def message_list(request):
    messages_qs = Message.objects.filter(teacher=request.user).select_related('student')
    students    = Student.objects.filter(teacher=request.user, active=True)
    classrooms  = Classroom.objects.filter(teacher=request.user)
    return render(request, 'students/message_list.html', {
        'messages_qs': messages_qs,
        'students': students,
        'classrooms': classrooms,
    })


@login_required
def message_create(request):
    students   = Student.objects.filter(teacher=request.user, active=True).select_related('classroom')
    classrooms = Classroom.objects.filter(teacher=request.user)
    preselect  = request.GET.get('student', '')

    if request.method == 'POST':
        p = request.POST
        student_ids = p.getlist('students')
        subject     = p.get('subject', '').strip()
        body        = p.get('body', '').strip()

        if not student_ids or not subject or not body:
            messages.error(request, 'Completa todos los campos obligatorios.')
        else:
            count = 0
            for sid in student_ids:
                try:
                    st = Student.objects.get(pk=sid, teacher=request.user)
                    Message.objects.create(
                        teacher=request.user,
                        student=st,
                        subject=subject,
                        body=body,
                    )
                    count += 1
                except Student.DoesNotExist:
                    pass
            messages.success(request, f'Mensaje enviado a {count} estudiante{"s" if count != 1 else ""}.')
            return redirect('students:message_list')

    return render(request, 'students/message_form.html', {
        'students': students,
        'classrooms': classrooms,
        'preselect': preselect,
    })


@login_required
def message_delete(request, pk):
    msg = get_object_or_404(Message, pk=pk, teacher=request.user)
    if request.method == 'POST':
        msg.delete()
        messages.success(request, 'Mensaje eliminado.')
    return redirect('students:message_list')


# ── PARENT PORTAL ────────────────────────────────────────────
def parent_portal(request):
    """Portal público para padres: galería + notas + mensajes por correo."""
    email   = request.GET.get('email', '').strip().lower()
    student = None
    works   = []
    grades  = []
    msgs    = []
    attendances = []

    if email:
        from gallery.models import StudentWork
        # Search by parent_email OR student email (iexact handles uppercase)
        student = Student.objects.filter(active=True).filter(
            Q(parent_email__iexact=email) | Q(email__iexact=email)
        ).first()
        # Fallback: handle stored emails with leading/trailing spaces
        if not student:
            student = Student.objects.filter(active=True).filter(
                Q(parent_email__icontains=email) | Q(email__icontains=email)
            ).first()
            if student:
                stored_pe = (student.parent_email or "").strip().lower()
                stored_e  = (student.email or "").strip().lower()
                if stored_pe != email and stored_e != email:
                    student = None

        if student:
            # Ensure teacher profile exists for subject display in template
            try:
                from accounts.models import TeacherProfile
                TeacherProfile.objects.get_or_create(user=student.teacher)
            except Exception:
                pass
            works       = StudentWork.objects.filter(student=student, is_public=True).order_by('-created_at')
            grades      = student.grades.order_by('-date')
            msgs        = student.messages.order_by('-sent_at')
            try:
                attendances = student.attendances.order_by('-date')
            except Exception:
                attendances = []
            student.messages.filter(is_read=False).update(is_read=True)

    return render(request, 'students/parent_portal.html', {
        'email': email,
        'student': student,
        'works': works,
        'grades': grades,
        'msgs': msgs,
        'attendances': attendances,
    })


def parent_portal_auto(request):
    """Auto-login para padres autenticados con Google OAuth."""
    if not request.user.is_authenticated:
        return redirect('/accounts/social/google/?next=/padres/auto/')
    email = request.user.email.strip().lower()
    if email:
        return redirect(f'/padres/?email={email}')
    return redirect('/padres/')
