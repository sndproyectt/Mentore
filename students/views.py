"""
Vistas del módulo students — Mentore.
Los profesores ven SOLO sus salones y estudiantes.
Compatible con el nuevo M2M Classroom.teachers.
"""
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Avg
from django.shortcuts import render, redirect, get_object_or_404

from .models import Classroom, Student, Announcement, Attendance, Message, DirectMessage

# ── helpers ──────────────────────────────────────────────────────────────────

def _teacher_classrooms(user):
    """Salones donde el usuario es propietario (FK) O está en la lista M2M."""
    return Classroom.objects.filter(
        Q(teacher=user) | Q(teachers=user)
    ).distinct()

# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    from datetime import date
    from grades.models import Grade

    classrooms      = _teacher_classrooms(request.user)
    shared_cr_ids   = request.user.shared_classrooms.values_list('id', flat=True)
    students_qs     = Student.objects.filter(
        Q(teacher=request.user) | Q(classroom_id__in=shared_cr_ids)
    ).filter(active=True).distinct()
    total_students  = students_qs.count()

    today           = date.today()
    _sid_qs         = students_qs.values_list('id', flat=True)
    present_today   = Attendance.objects.filter(
        student_id__in=_sid_qs, date=today, status='present'
    ).count()
    absent_today    = Attendance.objects.filter(
        student_id__in=_sid_qs, date=today, status='absent'
    ).count()

    grades_qs       = Grade.objects.filter(student_id__in=_sid_qs)
    total_grades    = grades_qs.count()
    avg_raw         = grades_qs.aggregate(Avg('score'))['score__avg']
    avg_grade       = round(avg_raw, 1) if avg_raw else 0

    unread_msgs     = Message.objects.filter(
        student_id__in=_sid_qs, is_read=False
    ).count()

    recent_students = students_qs.order_by('-created_at')[:6]

    announcements   = Announcement.objects.filter(
        teacher=request.user
    ).order_by('-created_at')[:4]

    return render(request, 'students/dashboard.html', {
        'classrooms':      classrooms,
        'total_students':  total_students,
        'present_today':   present_today,
        'absent_today':    absent_today,
        'total_grades':    total_grades,
        'avg_grade':       avg_grade,
        'unread_msgs':     unread_msgs,
        'recent_students': recent_students,
        'announcements':   announcements,
    })

# ── Classrooms ────────────────────────────────────────────────────────────────

@login_required
def classroom_list(request):
    classrooms = _teacher_classrooms(request.user).prefetch_related('teachers')
    return render(request, 'students/classroom_list.html', {'classrooms': classrooms})


@login_required
def classroom_create(request):
    """Profesores pueden crear sus propios salones."""
    if request.method == 'POST':
        p = request.POST
        cr = Classroom.objects.create(
            teacher=request.user,
            name=p.get('name', ''),
            grade_level=p.get('grade_level', ''),
            subject=p.get('subject', ''),
        )
        cr.teachers.add(request.user)   # el creador entra al M2M también
        messages.success(request, f'Grupo «{cr.name}» creado exitosamente.')
        return redirect('students:classrooms')
    return render(request, 'students/classroom_form.html', {'action': 'Crear'})


@login_required
def classroom_edit(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk, teacher=request.user)
    if request.method == 'POST':
        p = request.POST
        classroom.name        = p.get('name', classroom.name)
        classroom.grade_level = p.get('grade_level', classroom.grade_level)
        classroom.subject     = p.get('subject', classroom.subject)
        classroom.save()
        messages.success(request, f'Grupo «{classroom.name}» actualizado.')
        return redirect('students:classrooms')
    return render(request, 'students/classroom_form.html', {
        'action': 'Editar', 'classroom': classroom
    })


@login_required
def classroom_delete(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk, teacher=request.user)
    if request.method == 'POST':
        name = classroom.name
        classroom.delete()
        messages.success(request, f'Grupo «{name}» eliminado.')
        return redirect('students:classrooms')
    return redirect('students:classrooms')

# ── Students ──────────────────────────────────────────────────────────────────

@login_required
def student_list(request):
    query        = request.GET.get('q', '')
    classroom_id = request.GET.get('classroom', '')
    shared_cr_ids = request.user.shared_classrooms.values_list('id', flat=True)
    students = Student.objects.filter(
        Q(teacher=request.user) | Q(classroom_id__in=shared_cr_ids)
    ).filter(active=True).distinct()
    if query:
        students = students.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)  |
            Q(document_id__icontains=query)
        )
    if classroom_id:
        students = students.filter(classroom_id=classroom_id)
    classrooms = _teacher_classrooms(request.user)
    return render(request, 'students/student_list.html', {
        'students':           students,
        'classrooms':         classrooms,
        'query':              query,
        'selected_classroom': classroom_id,
    })


@login_required
def student_create(request):
    classrooms = _teacher_classrooms(request.user)
    if request.method == 'POST':
        p = request.POST
        Student.objects.create(
            teacher=request.user,
            classroom_id=p.get('classroom') or None,
            first_name=p.get('first_name', ''),
            last_name=p.get('last_name', ''),
            document_id=p.get('document_id', ''),
            email=p.get('email', ''),
            parent_email=p.get('parent_email', ''),
            parent_name=p.get('parent_name', ''),
            parent_phone=p.get('parent_phone', ''),
            gender=p.get('gender', ''),
            notes=p.get('notes', ''),
            date_of_birth=p.get('date_of_birth') or None,
        )
        messages.success(request, 'Estudiante creado correctamente.')
        return redirect('students:list')
    return render(request, 'students/student_form.html', {
        'classrooms': classrooms, 'action': 'Crear',
    })


@login_required
def student_detail(request, pk):
    shared_cr_ids    = request.user.shared_classrooms.values_list('id', flat=True)
    student          = get_object_or_404(
        Student.objects.filter(
            Q(teacher=request.user) | Q(classroom_id__in=shared_cr_ids)
        ).distinct(),
        pk=pk
    )
    grades           = student.grades.select_related('subject').order_by('subject__name', '-date')
    all_attendances  = student.attendances.order_by('-date')
    present          = all_attendances.filter(status='present').count()
    absent           = all_attendances.filter(status='absent').count()
    attendances      = all_attendances[:30]
    messages_sent    = student.messages.order_by('-sent_at')[:10]
    return render(request, 'students/student_detail.html', {
        'student':       student,
        'grades':        grades,
        'attendances':   attendances,
        'present':       present,
        'absent':        absent,
        'messages_sent': messages_sent,
    })


@login_required
def student_edit(request, pk):
    shared_cr_ids = request.user.shared_classrooms.values_list('id', flat=True)
    student    = get_object_or_404(
        Student.objects.filter(
            Q(teacher=request.user) | Q(classroom_id__in=shared_cr_ids)
        ).distinct(),
        pk=pk
    )
    classrooms = _teacher_classrooms(request.user)
    if request.method == 'POST':
        p = request.POST
        student.first_name   = p.get('first_name', student.first_name)
        student.last_name    = p.get('last_name',  student.last_name)
        student.document_id  = p.get('document_id', student.document_id)
        student.email        = p.get('email', student.email)
        student.parent_email = p.get('parent_email', student.parent_email)
        student.parent_name  = p.get('parent_name', student.parent_name)
        student.parent_phone = p.get('parent_phone', student.parent_phone)
        student.gender       = p.get('gender', student.gender)
        student.notes        = p.get('notes', student.notes)
        student.classroom_id = p.get('classroom') or None
        if p.get('date_of_birth'):
            student.date_of_birth = p.get('date_of_birth')
        if request.FILES.get('photo'):
            student.photo = request.FILES['photo']
        student.save()
        messages.success(request, f'{student.get_full_name()} actualizado.')
        return redirect('students:detail', pk=student.pk)
    return render(request, 'students/student_form.html', {
        'classrooms': classrooms, 'student': student, 'action': 'Editar',
    })


@login_required
def student_delete(request, pk):
    shared_cr_ids = request.user.shared_classrooms.values_list('id', flat=True)
    student = get_object_or_404(
        Student.objects.filter(
            Q(teacher=request.user) | Q(classroom_id__in=shared_cr_ids)
        ).distinct(),
        pk=pk
    )
    if request.method == 'POST':
        name = student.get_full_name()
        student.active = False
        student.save()
        messages.success(request, f'{name} ha sido desactivado.')
        return redirect('students:list')
    return redirect('students:list')

# ── Attendance ────────────────────────────────────────────────────────────────

@login_required
def attendance_view(request):
    classrooms       = _teacher_classrooms(request.user)
    selected_date    = request.GET.get('date', '')
    selected_classroom = request.GET.get('classroom', '')
    students         = []
    attendance_map   = {}
    status_choices   = Attendance.STATUS_CHOICES

    if not selected_date:
        from datetime import date
        selected_date = date.today().isoformat()

    if selected_classroom:
        classroom = get_object_or_404(
            Classroom, pk=selected_classroom
        )
        if not classroom.has_teacher_access(request.user):
            messages.error(request, 'No tienes acceso a ese salón.')
            return redirect('students:attendance')
        students = Student.objects.filter(
            classroom=classroom, active=True
        ).order_by('last_name', 'first_name')
        existing = Attendance.objects.filter(
            student__in=students, date=selected_date
        )
        attendance_map = {a.student_id: a for a in existing}

    return render(request, 'students/attendance.html', {
        'classrooms':         classrooms,
        'students':           students,
        'attendance_map':     attendance_map,
        'selected_date':      selected_date,
        'selected_classroom': selected_classroom,
        'status_choices':     status_choices,
    })


@login_required
def save_attendance(request):
    if request.method != 'POST':
        return redirect('students:attendance')

    classroom_id = request.POST.get('classroom_id')
    date_str     = request.POST.get('date')
    classroom    = get_object_or_404(Classroom, pk=classroom_id)

    if not classroom.has_teacher_access(request.user):
        messages.error(request, 'No tienes permiso para guardar asistencia en este salón.')
        return redirect('students:attendance')

    from django.urls import reverse as _reverse
    students_qs = Student.objects.filter(classroom=classroom, active=True)                        .prefetch_related('guardians')

    for student in students_qs:
        status = request.POST.get(f'status_{student.pk}', 'present')
        note   = request.POST.get(f'note_{student.pk}', '')
        att, created = Attendance.objects.update_or_create(
            student=student, date=date_str,
            defaults={'status': status, 'note': note}
        )
        # ── Notificación Gmail para ausencia o llegada tarde ──
        if status in ('absent', 'late'):
            _send_attendance_notification(
                teacher=request.user,
                student=student,
                classroom=classroom,
                date_str=date_str,
                status=status,
                note=note,
            )

    messages.success(request, f'Asistencia del {date_str} guardada correctamente.')
    return redirect(
        f"{_reverse('students:attendance')}"
        f"?classroom={classroom_id}&date={date_str}"
    )


def _send_attendance_notification(teacher, student, classroom, date_str, status, note):
    """
    Envía notificación por Gmail al acudiente principal del estudiante.
    Falla silenciosamente para no interrumpir el flujo de asistencia.
    """
    try:
        from gmail_service import send_gmail_message
        from django.template.loader import render_to_string
        from django.utils.dateparse import parse_date

        # 1. Obtener acudiente principal
        guardian = student.guardians.filter(is_primary=True, email__gt='').first()
        if not guardian:
            # Fallback al campo legacy parent_email
            if not student.parent_email:
                return
            guardian_name  = student.parent_name or 'Acudiente'
            guardian_email = student.parent_email
        else:
            guardian_name  = guardian.name
            guardian_email = guardian.email

        # 2. Datos del colegio
        school_name = getattr(
            getattr(teacher, 'teacher_profile', None), 'school_name', ''
        ) or 'Colegio'

        # 3. Fecha legible
        parsed_date = parse_date(date_str)
        from django.utils.formats import date_format
        date_display = date_format(parsed_date, 'l j \\d\\e F \\d\\e Y') if parsed_date else date_str

        ctx = {
            'guardian_name': guardian_name,
            'student_name':  student.get_full_name(),
            'date':          date_display,
            'classroom':     classroom.name,
            'teacher_name':  teacher.get_full_name() or teacher.username,
            'school_name':   school_name,
            'note':          note,
        }

        # 4. Elegir template según status
        if status == 'absent':
            template = 'students/emails/absent_email.html'
            subject  = f'Ausencia de {student.get_full_name()} — {date_display}'
        else:  # late
            template = 'students/emails/late_email.html'
            subject  = f'Llegada tarde de {student.get_full_name()} — {date_display}'

        html_body = render_to_string(template, ctx)

        # 5. Enviar
        send_gmail_message(
            teacher_user=teacher,
            to_email=guardian_email,
            subject=subject,
            html_body=html_body,
        )

    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            'Error enviando notificación Gmail para %s: %s', student, exc
        )

# ── Announcements ─────────────────────────────────────────────────────────────

@login_required
def announcement_list(request):
    announcements = Announcement.objects.filter(
        teacher=request.user
    ).order_by('-created_at')
    classrooms = _teacher_classrooms(request.user)
    return render(request, 'students/announcement_list.html', {
        'announcements': announcements, 'classrooms': classrooms,
    })


@login_required
def announcement_create(request):
    from django.contrib.auth.models import User
    classrooms           = _teacher_classrooms(request.user)
    all_teachers         = User.objects.exclude(pk=request.user.pk).filter(
        teacher_profile__isnull=False
    ).order_by('last_name', 'first_name').select_related('teacher_profile')
    _role = getattr(getattr(request.user, 'teacher_profile', None), 'role', 'teacher')
    if _role == 'coordinator':
        students_with_parent = Student.objects.filter(active=True)            .exclude(parent_email='').select_related('classroom').order_by('last_name')
    else:
        students_with_parent = Student.objects.filter(
            teacher=request.user, active=True
        ).exclude(parent_email='').select_related('classroom').order_by('last_name')

    if request.method == 'POST':
        p             = request.POST
        title         = p.get('title', '').strip()
        content_txt   = p.get('content', '').strip()
        priority      = p.get('priority', 'low')
        t_ids         = p.getlist('teacher_recipients')
        s_ids         = p.getlist('parent_recipients')

        if not title or not content_txt:
            messages.error(request, 'El título y el contenido son obligatorios.')
        elif not t_ids and not s_ids:
            messages.error(request, 'Selecciona al menos un destinatario.')
        else:
            ann = Announcement.objects.create(
                teacher=request.user,
                title=title,
                content=content_txt,
                priority=priority,
            )
            if t_ids:
                ann.teacher_recipients.set(t_ids)
            if s_ids:
                ann.student_recipients.set(s_ids)
            total = len(t_ids) + len(s_ids)
            messages.success(request, f'Comunicado publicado para {total} destinatario(s).')
            return redirect('students:announcement_list')

    return render(request, 'students/announcement_form.html', {
        'classrooms':           classrooms,
        'all_teachers':         all_teachers,
        'students_with_parent': students_with_parent,
    })


@login_required
def announcement_delete(request, pk):
    ann = get_object_or_404(Announcement, pk=pk, teacher=request.user)
    if request.method == 'POST':
        ann.delete()
        messages.success(request, 'Comunicado eliminado.')
    return redirect('students:announcement_list')

# ── Messages ──────────────────────────────────────────────────────────────────

@login_required
def message_list(request):
    query        = request.GET.get('q', '')
    classroom_id = request.GET.get('classroom', '')
    students_qs  = Student.objects.filter(teacher=request.user, active=True)
    if query:
        students_qs = students_qs.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
    if classroom_id:
        students_qs = students_qs.filter(classroom_id=classroom_id)
    classrooms = _teacher_classrooms(request.user)
    return render(request, 'students/message_list.html', {
        'students':           students_qs,
        'classrooms':         classrooms,
        'query':              query,
        'selected_classroom': classroom_id,
    })


@login_required
def message_send(request, student_pk):
    _sc_ids = request.user.shared_classrooms.values_list('id', flat=True)
    student = get_object_or_404(
        Student.objects.filter(
            Q(teacher=request.user) | Q(classroom_id__in=_sc_ids)
        ).distinct(),
        pk=student_pk
    )
    if request.method == 'POST':
        p = request.POST
        grade_level = p.get('grade_level', '')
        subject_val = p.get('subject',     '')
        body_val    = p.get('body',        '')
        if not subject_val or not body_val:
            messages.error(request, 'El asunto y el mensaje son obligatorios.')
        else:
            Message.objects.create(
                teacher=request.user,
                student=student,
                subject=subject_val,
                body=body_val,
            )
            messages.success(request, f'Mensaje enviado a {student.get_full_name()}.')
            return redirect('students:message_list')
    return render(request, 'students/message_send.html', {'student': student})

# ── Parent Portal ─────────────────────────────────────────────────────────────

def parent_portal(request):
    email    = ''
    student  = None
    works    = []
    grades   = []
    msgs     = []
    attendances = []
    subjects_data = []
    general_avg = None

    # Accept both POST (from login page) and GET (legacy direct URL)
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
    elif request.GET.get('email'):
        email = request.GET.get('email', '').strip().lower()

    if email:
        try:
            student = Student.objects.select_related(
                'teacher', 'teacher__teacher_profile', 'classroom'
            ).get(parent_email__iexact=email, active=True)
            # Asegurar que el perfil del profesor exista
            from accounts.models import TeacherProfile
            TeacherProfile.objects.get_or_create(user=student.teacher)
        except Student.DoesNotExist:
            student = None

        if student:
            from gallery.models import StudentWork
            works  = StudentWork.objects.filter(
                student=student, is_public=True
            ).order_by('-created_at')
            grades = list(student.grades.select_related('subject').order_by('subject__name', '-date'))
            msgs   = student.messages.order_by('-sent_at')
            try:
                attendances = student.attendances.order_by('-date')
            except Exception:
                attendances = []
            student.messages.filter(is_read=False).update(is_read=True)

            # Agrupar notas por materia
            _sd = {}
            for g in grades:
                key  = g.subject_id if g.subject else f'txt_{g.subject_text}'
                name = g.subject.name if g.subject else (g.subject_text or 'Sin materia')
                if key not in _sd:
                    _sd[key] = {'name': name, 'grades': [], 'avg': None}
                _sd[key]['grades'].append(g)
            for key, data in _sd.items():
                sc = [float(g.score) for g in data['grades']]
                data['avg'] = round(sum(sc)/len(sc), 2) if sc else None
            subjects_data = list(_sd.values())
            all_sc = [float(g.score) for g in grades]
            general_avg = round(sum(all_sc)/len(all_sc), 2) if all_sc else None
        else:
            subjects_data = []
            general_avg   = None

    from django.contrib.auth.models import User as AuthUser
    all_staff = AuthUser.objects.filter(
        teacher_profile__isnull=False
    ).order_by('teacher_profile__role', 'last_name').select_related('teacher_profile')
    guardians = student.guardians.all() if student else []

    return render(request, 'students/parent_portal.html', {
        'email':         email,
        'student':       student,
        'works':         works,
        'grades':        grades,
        'msgs':          msgs,
        'attendances':   attendances,
        'subjects_data': subjects_data,
        'general_avg':   general_avg,
        'all_staff':     all_staff,
        'guardians':     guardians,
    })


# ── Message create / delete (URLs legacy) ────────────────────────────────────

@login_required
def message_create(request):
    """Mensaje a docentes (DirectMessage) y/o padres (Message vinculado a estudiante)."""
    from django.contrib.auth.models import User
    classrooms           = _teacher_classrooms(request.user)
    all_teachers         = User.objects.exclude(pk=request.user.pk).filter(
        teacher_profile__isnull=False
    ).order_by('last_name', 'first_name').select_related('teacher_profile')
    _role = getattr(getattr(request.user, 'teacher_profile', None), 'role', 'teacher')
    if _role == 'coordinator':
        students_with_parent = Student.objects.filter(active=True)            .exclude(parent_email='').select_related('classroom').order_by('last_name')
    else:
        students_with_parent = Student.objects.filter(
            teacher=request.user, active=True
        ).exclude(parent_email='').select_related('classroom').order_by('last_name')

    if request.method == 'POST':
        p             = request.POST
        subject_val   = p.get('subject', '').strip()
        body_val      = p.get('body', '').strip()
        t_ids         = p.getlist('teacher_recipients')
        s_ids         = p.getlist('parent_recipients')

        if not subject_val or not body_val:
            messages.error(request, 'El asunto y el mensaje son obligatorios.')
        elif not t_ids and not s_ids:
            messages.error(request, 'Selecciona al menos un destinatario.')
        else:
            count = 0
            # Mensajes a docentes (DirectMessage)
            for tid in t_ids:
                try:
                    recipient = User.objects.get(pk=tid)
                    DirectMessage.objects.create(
                        sender=request.user,
                        recipient=recipient,
                        subject=subject_val,
                        body=body_val,
                    )
                    count += 1
                except User.DoesNotExist:
                    pass
            # Mensajes a padres (Message vinculado a estudiante)
            for sid in s_ids:
                try:
                    student = Student.objects.get(pk=sid, active=True)
                    Message.objects.create(
                        teacher=request.user,
                        student=student,
                        subject=subject_val,
                        body=body_val,
                    )
                    count += 1
                except Student.DoesNotExist:
                    pass
            messages.success(request, f'Mensaje enviado a {count} destinatario(s).')
            return redirect('students:message_list')

    return render(request, 'students/message_form.html', {
        'classrooms':           classrooms,
        'all_teachers':         all_teachers,
        'students_with_parent': students_with_parent,
    })
@login_required
def message_delete(request, pk):
    msg = get_object_or_404(Message, pk=pk, teacher=request.user)
    if request.method == 'POST':
        msg.delete()
        messages.success(request, 'Mensaje eliminado.')
    return redirect('students:message_list')


# ── Schedule ──────────────────────────────────────────────────────────────────

@login_required
def schedule_view(request):
    classrooms = _teacher_classrooms(request.user)
    return render(request, 'students/schedule.html', {
        'classrooms':    classrooms,
        'days':          ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'],
        'hours':         ['6:00', '7:00', '8:00', '9:00', '10:00', '11:00',
                          '12:00', '1:00', '2:00', '3:00', '4:00', '5:00'],
        'day_numbers':   ['1', '2', '3', '4', '5'],
        'subject_colors': ['#E8EAF6', '#E8F5E9', '#FFF8E1',
                           '#FCE4EC', '#E0F2F1', '#F3E5F5', '#FFF3F0'],
    })


# ── Parent portal auto (URL legacy) ──────────────────────────────────────────

def parent_portal_auto(request):
    """
    Acceso directo al portal del padre con email en GET (?email=...).
    Compatible con la URL legacy /padres/auto/.
    """
    email = request.GET.get('email', '').strip().lower()
    student = None
    works = grades = msgs = attendances = []

    if email:
        try:
            from accounts.models import TeacherProfile
            student = Student.objects.select_related(
                'teacher', 'teacher__teacher_profile', 'classroom'
            ).get(parent_email__iexact=email, active=True)
            TeacherProfile.objects.get_or_create(user=student.teacher)
            from gallery.models import StudentWork
            works       = StudentWork.objects.filter(student=student, is_public=True).order_by('-created_at')
            grades      = student.grades.order_by('-date')
            msgs        = student.messages.order_by('-sent_at')
            attendances = student.attendances.order_by('-date')
            student.messages.filter(is_read=False).update(is_read=True)
        except Student.DoesNotExist:
            student = None

    return render(request, 'students/parent_portal.html', {
        'email': email, 'student': student,
        'works': works, 'grades': grades,
        'msgs': msgs, 'attendances': attendances,
    })


# ── Inbox: comunicados y mensajes RECIBIDOS por el docente ────────────────────

@login_required
def inbox_view(request):
    """Bandeja de entrada: comunicados + DirectMessages + mensajes de padres."""
    received_announcements = Announcement.objects.filter(
        teacher_recipients=request.user
    ).select_related('teacher').order_by('-created_at')

    from django.db.models import Prefetch as _Prefetch, Q as _Q

    # DirectMessages de docente a docente (hilos, solo raíz)
    _dm_replies_qs = DirectMessage.objects.select_related('sender').order_by('sent_at')
    received_direct = DirectMessage.objects.filter(
        recipient=request.user,
        reply_to__isnull=True,
    ).select_related('sender').prefetch_related(
        _Prefetch('replies', queryset=_dm_replies_qs, to_attr='replies_asc')
    ).order_by('-sent_at')

    # Mensajes raíz donde este usuario es el teacher,
    # O donde este usuario tiene al menos una respuesta en el hilo
    root_ids_as_teacher = Message.objects.filter(
        teacher=request.user, reply_to__isnull=True
    ).values_list('pk', flat=True)
    root_ids_via_reply = Message.objects.filter(
        teacher=request.user, reply_to__isnull=False
    ).values_list('reply_to_id', flat=True)
    all_root_ids = set(root_ids_as_teacher) | set(root_ids_via_reply)
    _replies_qs = Message.objects.select_related('teacher').order_by('sent_at')
    parent_messages = Message.objects.filter(
        pk__in=all_root_ids,
    ).select_related('student').prefetch_related(
        _Prefetch('replies', queryset=_replies_qs)
    ).order_by('-sent_at')

    DirectMessage.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    Message.objects.filter(teacher=request.user, is_read=False).update(is_read=True)

    unread_count = (
        DirectMessage.objects.filter(recipient=request.user, is_read=False).count() +
        Message.objects.filter(teacher=request.user, is_read=False, sender_label='padre').count()
    )

    return render(request, 'students/inbox.html', {
        'received_announcements': received_announcements,
        'received_direct':        received_direct,
        'parent_messages':        parent_messages,
        'unread_count':           unread_count,
    })


@login_required
def direct_message_reply(request, pk):
    """Responder a un DirectMessage (hilo tipo chat)."""
    original = get_object_or_404(DirectMessage, pk=pk)
    # Only sender or recipient can reply
    if request.user not in (original.sender, original.recipient):
        messages.error(request, 'Sin acceso a este hilo.')
        return redirect('students:inbox')
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if not body:
            messages.error(request, 'El mensaje no puede estar vacío.')
        else:
            # Reply goes to the other person
            recipient = original.recipient if request.user == original.sender else original.sender
            DirectMessage.objects.create(
                sender=request.user,
                recipient=recipient,
                subject=f'Re: {original.subject}',
                body=body,
                reply_to=original,
            )
            messages.success(request, 'Respuesta enviada.')
    return redirect('students:inbox')

@login_required
def message_thread(request, pk):
    """Hilo de un mensaje con historial + opción de reply (docente/coordinador)."""
    msg = get_object_or_404(Message, pk=pk)
    # Walk up to root
    root = msg
    while root.reply_to_id:
        root = root.reply_to
    # Security: teacher of root must be request.user (or any reply teacher)
    all_teachers_in_thread = set(
        Message.objects.filter(
            Q(pk=root.pk) | Q(reply_to=root)
        ).values_list('teacher_id', flat=True)
    )
    if request.user.pk not in all_teachers_in_thread:
        messages.error(request, 'Sin acceso.')
        return redirect('students:message_list')
    # Full thread ordered oldest→newest
    thread = [root] + list(root.replies.order_by('sent_at'))
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body:
            Message.objects.create(
                teacher=request.user,
                student=msg.student,
                subject=f'Re: {msg.subject}',
                body=body,
                reply_to=msg,
                sender_label=request.user.get_full_name() or request.user.username,
            )
            messages.success(request, 'Respuesta enviada.')
        # Redirect back to inbox if came from there, else message_thread
        next_url = request.POST.get('next', '')
        if next_url == 'inbox':
            return redirect('students:inbox')
        return redirect('students:message_thread', pk=msg.pk)
    return render(request, 'students/message_thread.html', {
        'root': msg, 'thread': thread,
    })


def parent_message_send(request):
    """Padre envía mensaje a un docente/coordinador específico desde el portal."""
    from django.contrib.auth.models import User as AuthUser
    send_success = False
    email        = request.POST.get('email', '').strip().lower() or request.GET.get('email', '').strip().lower()
    subject_val  = request.POST.get('subject', '').strip()
    body_val     = request.POST.get('body', '').strip()
    recipient_id = request.POST.get('recipient_id', '').strip()

    student = None
    if email:
        try:
            student = Student.objects.select_related('teacher', 'classroom').get(parent_email__iexact=email, active=True)
        except Student.DoesNotExist:
            student = None

    if request.method == 'POST' and student and subject_val and body_val and recipient_id:
        try:
            recipient = AuthUser.objects.get(pk=recipient_id)
            # Check if this is a reply to an existing thread
            # A reply subject looks like "Re: <original>" — find the root
            root_msg  = None
            clean_subj = subject_val
            if subject_val.startswith('Re: '):
                original_subj = subject_val[4:]
                # Find root (reply_to=None) message in this student's history with that subject
                root_msg = Message.objects.filter(
                    student=student,
                    subject=original_subj,
                    reply_to__isnull=True,
                ).order_by('sent_at').first()
                clean_subj = original_subj

            if root_msg:
                Message.objects.create(
                    teacher=recipient,
                    student=student,
                    subject=f'Re: {clean_subj}',
                    body=body_val,
                    sender_label='padre',
                    reply_to=root_msg,
                )
            else:
                Message.objects.create(
                    teacher=recipient,
                    student=student,
                    subject=clean_subj,
                    body=body_val,
                    sender_label='padre',
                )
            send_success = True
        except AuthUser.DoesNotExist:
            pass

    # Re-render portal with success flag
    works = grades = msgs = attendances = []
    subjects_data = []
    general_avg   = None
    if student:
        from gallery.models import StudentWork
        from accounts.models import TeacherProfile
        TeacherProfile.objects.get_or_create(user=student.teacher)
        works       = StudentWork.objects.filter(student=student, is_public=True).order_by('-created_at')
        grades      = list(student.grades.select_related('subject').order_by('subject__name', '-date'))
        msgs        = student.messages.order_by('-sent_at')
        attendances = student.attendances.order_by('-date')
        _sd = {}
        for g in grades:
            key  = g.subject_id if g.subject else f'txt_{g.subject_text}'
            name = g.subject.name if g.subject else (g.subject_text or 'Sin materia')
            if key not in _sd:
                _sd[key] = {'name': name, 'grades': [], 'avg': None}
            _sd[key]['grades'].append(g)
        for key, data in _sd.items():
            sc = [float(g.score) for g in data['grades']]
            data['avg'] = round(sum(sc)/len(sc), 2) if sc else None
        subjects_data = list(_sd.values())
        all_sc = [float(g.score) for g in grades]
        general_avg   = round(sum(all_sc)/len(all_sc), 2) if all_sc else None

    from django.contrib.auth.models import User as AuthUser
    all_staff = AuthUser.objects.filter(
        teacher_profile__isnull=False
    ).order_by('teacher_profile__role', 'last_name').select_related('teacher_profile')

    return render(request, 'students/parent_portal.html', {
        'email':         email,
        'student':       student,
        'works':         works,
        'grades':        grades,
        'msgs':          msgs,
        'attendances':   attendances,
        'subjects_data': subjects_data,
        'general_avg':   general_avg,
        'send_success':  send_success,
        'open_tab':      't-send',
        'all_staff':     all_staff,
    })