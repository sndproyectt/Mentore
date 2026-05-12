"""
Vistas del panel de Coordinación — Mentore.
El coordinador tiene acceso total: crea salones, asigna MÚLTIPLES docentes
por salón (M2M), gestiona roles, ve comunicados globales y supervisa todo.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Q

from accounts.decorators import coordinator_required
from accounts.models import TeacherProfile, ROLE_CHOICES
from accounts.forms import CoordinatorCreateTeacherForm
from students.models import Classroom, Student, Announcement, DirectMessage, Message
from grades.models import Grade, Subject, TeacherSubject

User = get_user_model()


# ── Helpers ────────────────────────────────────────────────────

def _all_teachers():
    """Todos los usuarios con perfil (profesor o coordinador)."""
    return (
        User.objects
        .filter(teacher_profile__isnull=False)
        .select_related('teacher_profile')
        .order_by('last_name', 'first_name')
    )


def _teacher_users():
    """Solo usuarios con rol teacher."""
    return (
        User.objects
        .filter(teacher_profile__role='teacher')
        .select_related('teacher_profile')
        .order_by('last_name', 'first_name')
    )


# ── Dashboard ──────────────────────────────────────────────────

@coordinator_required
def coordinator_dashboard(request):
    total_classrooms = Classroom.objects.count()
    total_students   = Student.objects.filter(active=True).count()
    total_teachers   = User.objects.filter(teacher_profile__role='teacher').count()
    total_announce   = Announcement.objects.count()
    avg_grade        = Grade.objects.aggregate(Avg('score'))['score__avg'] or 0

    classrooms_summary = (
        Classroom.objects
        .select_related('teacher', 'teacher__teacher_profile')
        .prefetch_related('teachers')
        .annotate(student_count=Count('students'))
        .order_by('teacher__last_name', 'name')[:10]
    )
    recent_announcements = (
        Announcement.objects
        .select_related('teacher', 'classroom')
        .order_by('-created_at')[:5]
    )
    teachers = (
        _teacher_users()
        .annotate(
            student_count=Count('students', filter=Q(students__active=True)),
            classroom_count=Count('classrooms'),
        )
    )
    total_subjects = Subject.objects.filter(active=True).count()
    subjects_summary = (
        Subject.objects
        .filter(active=True)
        .prefetch_related('teacher_assignments', 'teacher_assignments__teacher')
        .annotate(grade_count=Count('grades'))
        .order_by('name')[:6]
    )

    context = {
        'total_classrooms':      total_classrooms,
        'total_students':        total_students,
        'total_teachers':        total_teachers,
        'total_announce':        total_announce,
        'total_subjects':        total_subjects,
        'avg_grade':             round(float(avg_grade), 1),
        'classrooms_summary':    classrooms_summary,
        'recent_announcements':  recent_announcements,
        'teachers':              teachers,
        'subjects_summary':      subjects_summary,
    }
    return render(request, 'coordinator/dashboard.html', context)


# ── Salones ────────────────────────────────────────────────────

@coordinator_required
def classroom_list(request):
    """Lista global de todos los salones con todos sus docentes."""
    q              = request.GET.get('q', '')
    teacher_filter = request.GET.get('teacher', '')

    classrooms = (
        Classroom.objects
        .select_related('teacher', 'teacher__teacher_profile')
        .prefetch_related('teachers', 'teachers__teacher_profile')
        .annotate(student_count=Count('students'))
    )
    if q:
        classrooms = classrooms.filter(
            Q(name__icontains=q) | Q(grade_level__icontains=q) | Q(subject__icontains=q)
        )
    if teacher_filter:
        classrooms = classrooms.filter(
            Q(teacher_id=teacher_filter) | Q(teachers__id=teacher_filter)
        ).distinct()

    classrooms = classrooms.order_by('name')
    teachers   = _all_teachers()

    return render(request, 'coordinator/classroom_list.html', {
        'classrooms':     classrooms,
        'teachers':       teachers,
        'q':              q,
        'teacher_filter': teacher_filter,
    })


@coordinator_required
def classroom_assign(request, classroom_id):
    """
    Asignar/quitar MÚLTIPLES docentes a un salón.
    El coordinador puede cambiar el docente principal y gestionar la lista M2M.
    """
    classroom = get_object_or_404(Classroom, pk=classroom_id)
    teachers  = _all_teachers()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        # ── Cambiar docente principal ──
        if action == 'set_main':
            teacher_id = request.POST.get('teacher_id', '').strip()
            if not teacher_id:
                messages.error(request, 'Debes seleccionar un docente.')
            else:
                new_teacher = get_object_or_404(User, pk=teacher_id)
                old_teacher = classroom.teacher
                classroom.teacher = new_teacher
                classroom.save()
                # El nuevo principal también debe estar en la lista M2M
                classroom.teachers.add(new_teacher)
                messages.success(
                    request,
                    f'Docente principal cambiado a {new_teacher.get_full_name()}.'
                )
                if old_teacher != new_teacher:
                    messages.info(
                        request,
                        f'{old_teacher.get_full_name()} sigue con acceso al salón. '
                        f'Quítalo manualmente si ya no debe tenerlo.'
                    )

        # ── Agregar docente a la lista M2M ──
        elif action == 'add_teacher':
            teacher_id = request.POST.get('teacher_id', '').strip()
            if not teacher_id:
                messages.error(request, 'Selecciona un docente para agregar.')
            else:
                teacher_to_add = get_object_or_404(User, pk=teacher_id)
                if classroom.teachers.filter(pk=teacher_to_add.pk).exists():
                    messages.warning(
                        request,
                        f'{teacher_to_add.get_full_name()} ya tiene acceso a este salón.'
                    )
                else:
                    classroom.teachers.add(teacher_to_add)
                    messages.success(
                        request,
                        f'{teacher_to_add.get_full_name()} ahora tiene acceso al salón «{classroom.name}».'
                    )

        # ── Quitar docente de la lista M2M ──
        elif action == 'remove_teacher':
            teacher_id = request.POST.get('teacher_id', '').strip()
            if teacher_id:
                teacher_to_remove = get_object_or_404(User, pk=teacher_id)
                if teacher_to_remove.pk == classroom.teacher_id:
                    messages.error(
                        request,
                        f'No puedes quitar al docente principal. '
                        f'Primero asigna otro docente principal.'
                    )
                else:
                    classroom.teachers.remove(teacher_to_remove)
                    messages.success(
                        request,
                        f'{teacher_to_remove.get_full_name()} ya no tiene acceso al salón.'
                    )

        return redirect('coordinator:classroom_assign', classroom_id=classroom.pk)

    # Docentes actuales del salón (M2M)
    current_teachers = classroom.teachers.all().select_related('teacher_profile')
    # Docentes disponibles = todos menos los que ya están en M2M
    available_teachers = teachers.exclude(
        pk__in=current_teachers.values_list('pk', flat=True)
    )

    return render(request, 'coordinator/classroom_assign.html', {
        'classroom':          classroom,
        'current_teachers':   current_teachers,
        'available_teachers': available_teachers,
        'all_teachers':       teachers,
    })


@coordinator_required
def classroom_create(request):
    """El coordinador crea un salón, elige docente principal y docentes extra."""
    teachers = _all_teachers()
    if request.method == 'POST':
        p          = request.POST
        teacher_id = p.get('teacher_id', '').strip()
        name       = p.get('name', '').strip()
        if not teacher_id or not name:
            messages.error(request, 'El nombre y el docente principal son obligatorios.')
        else:
            teacher  = get_object_or_404(User, pk=teacher_id)
            classroom = Classroom.objects.create(
                teacher=teacher,
                name=name,
                grade_level=p.get('grade_level', ''),
                subject=p.get('subject', ''),
            )
            # Docente principal siempre entra al M2M
            classroom.teachers.add(teacher)
            # Docentes adicionales opcionales
            extra_ids = p.getlist('extra_teachers')
            for eid in extra_ids:
                try:
                    extra = User.objects.get(pk=eid)
                    classroom.teachers.add(extra)
                except User.DoesNotExist:
                    pass
            messages.success(
                request,
                f'Salón «{name}» creado y asignado a {teacher.get_full_name()}.'
            )
            return redirect('coordinator:classroom_list')
    return render(request, 'coordinator/classroom_create.html', {'teachers': teachers})


@coordinator_required
def classroom_delete(request, classroom_id):
    """Elimina un salón (solo si no tiene estudiantes activos)."""
    classroom = get_object_or_404(Classroom, pk=classroom_id)
    if request.method == 'POST':
        if classroom.students.filter(active=True).exists():
            messages.error(
                request,
                f'No se puede eliminar «{classroom.name}» porque tiene estudiantes activos. '
                f'Mueve o elimina los estudiantes primero.'
            )
        else:
            name = classroom.name
            classroom.delete()
            messages.success(request, f'Salón «{name}» eliminado.')
            return redirect('coordinator:classroom_list')
    return redirect('coordinator:classroom_list')


# ── Profesores ─────────────────────────────────────────────────

@coordinator_required
def teacher_list(request):
    q = request.GET.get('q', '')
    teachers = (
        _all_teachers()
        .annotate(
            student_count=Count('students', filter=Q(students__active=True)),
            classroom_count=Count('classrooms'),
        )
    )
    if q:
        teachers = teachers.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(email__icontains=q)      | Q(teacher_profile__subject__icontains=q)
        )
    return render(request, 'coordinator/teacher_list.html', {
        'teachers': teachers, 'q': q,
    })


@coordinator_required
def teacher_detail(request, teacher_id):
    teacher    = get_object_or_404(User, pk=teacher_id)
    profile, _ = TeacherProfile.objects.get_or_create(user=teacher)
    classrooms = (
        Classroom.objects
        .filter(Q(teacher=teacher) | Q(teachers=teacher))
        .distinct()
        .annotate(student_count=Count('students'))
    )
    announce = Announcement.objects.filter(teacher=teacher).order_by('-created_at')[:5]
    return render(request, 'coordinator/teacher_detail.html', {
        'teacher': teacher, 'profile': profile,
        'classrooms': classrooms, 'announce': announce,
    })


@coordinator_required
def teacher_change_role(request, teacher_id):
    teacher = get_object_or_404(User, pk=teacher_id)
    profile, _ = TeacherProfile.objects.get_or_create(user=teacher)
    if request.method == 'POST':
        new_role = request.POST.get('role', 'teacher')
        if new_role not in dict(ROLE_CHOICES):
            messages.error(request, 'Rol no válido.')
        else:
            profile.role = new_role
            profile.save()
            messages.success(
                request,
                f'Rol de {teacher.get_full_name()} cambiado a {profile.get_role_display()}.'
            )
            return redirect('coordinator:teacher_list')
    return render(request, 'coordinator/teacher_change_role.html', {
        'teacher': teacher, 'profile': profile,
    })


@coordinator_required
def teacher_create(request):
    form = CoordinatorCreateTeacherForm()
    if request.method == 'POST':
        form = CoordinatorCreateTeacherForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile, _ = TeacherProfile.objects.get_or_create(user=user)
            profile.role    = form.cleaned_data.get('role', 'teacher')
            profile.subject = form.cleaned_data.get('subject', '')
            profile.save()
            messages.success(request, f'Usuario {user.get_full_name()} creado correctamente.')
            return redirect('coordinator:teacher_list')
    return render(request, 'coordinator/teacher_create.html', {'form': form})


# ── Comunicados ────────────────────────────────────────────────

@coordinator_required
def announcement_list(request):
    q               = request.GET.get('q', '')
    teacher_filter  = request.GET.get('teacher', '')
    priority_filter = request.GET.get('priority', '')

    announcements = Announcement.objects.select_related('teacher', 'classroom')
    if q:
        announcements = announcements.filter(
            Q(title__icontains=q) | Q(content__icontains=q)
        )
    if teacher_filter:
        announcements = announcements.filter(teacher_id=teacher_filter)
    if priority_filter:
        announcements = announcements.filter(priority=priority_filter)

    announcements = announcements.order_by('-created_at')
    teachers      = _all_teachers()

    return render(request, 'coordinator/announcement_list.html', {
        'announcements':    announcements,
        'teachers':         teachers,
        'q':                q,
        'teacher_filter':   teacher_filter,
        'priority_filter':  priority_filter,
        'priority_choices': Announcement.PRIORITY_CHOICES,
    })


@coordinator_required
def announcement_create(request):
    all_teachers = _all_teachers()
    # Todos los estudiantes con email de padre (de cualquier docente)
    students_with_parent = Student.objects.filter(
        active=True
    ).exclude(parent_email='').select_related('classroom','teacher').order_by('last_name')
    classrooms = Classroom.objects.order_by('name')

    if request.method == 'POST':
        p           = request.POST
        title       = p.get('title', '').strip()
        content_txt = p.get('content', '').strip()
        priority    = p.get('priority', 'low')
        t_ids       = p.getlist('teacher_recipients')
        s_ids       = p.getlist('parent_recipients')

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
            return redirect('coordinator:announcement_list')

    return render(request, 'coordinator/announcement_create.html', {
        'all_teachers':         all_teachers,
        'students_with_parent': students_with_parent,
        'classrooms':           classrooms,
        'priority_choices':     Announcement.PRIORITY_CHOICES,
    })

@coordinator_required
def announcement_delete(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        ann.delete()
        messages.success(request, 'Comunicado eliminado.')
    return redirect('coordinator:announcement_list')


# ── Estudiantes (vista global) ─────────────────────────────────

@coordinator_required
def student_list(request):
    q              = request.GET.get('q', '')
    classroom_id   = request.GET.get('classroom', '')
    teacher_filter = request.GET.get('teacher', '')

    students = Student.objects.filter(active=True).select_related('teacher', 'classroom')
    if q:
        students = students.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(document_id__icontains=q)
        )
    if classroom_id:
        students = students.filter(classroom_id=classroom_id)
    if teacher_filter:
        students = students.filter(teacher_id=teacher_filter)

    classrooms = Classroom.objects.order_by('name')
    teachers   = _all_teachers()

    return render(request, 'coordinator/student_list.html', {
        'students':       students,
        'classrooms':     classrooms,
        'teachers':       teachers,
        'q':              q,
        'classroom_id':   classroom_id,
        'teacher_filter': teacher_filter,
    })


# ── Materias ───────────────────────────────────────────────────

@coordinator_required
def subject_list(request):
    """Lista de todas las materias y sus docentes asignados."""
    subjects = Subject.objects.prefetch_related(
        'teacher_assignments', 'teacher_assignments__teacher',
        'teacher_assignments__teacher__teacher_profile'
    ).annotate(grade_count=Count('grades'))
    return render(request, 'coordinator/subject_list.html', {
        'subjects': subjects,
    })


@coordinator_required
def subject_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        desc = request.POST.get('description', '').strip()
        if not name:
            messages.error(request, 'El nombre de la materia es obligatorio.')
        elif Subject.objects.filter(name__iexact=name).exists():
            messages.error(request, f'Ya existe una materia llamada «{name}».')
        else:
            Subject.objects.create(name=name, code=code, description=desc)
            messages.success(request, f'Materia «{name}» creada.')
            return redirect('coordinator:subject_list')
    return render(request, 'coordinator/subject_form.html', {'action': 'Crear'})


@coordinator_required
def subject_assign(request, subject_id):
    """Asignar/quitar docentes a una materia."""
    subject   = get_object_or_404(Subject, pk=subject_id)
    all_users = _all_teachers()

    if request.method == 'POST':
        action     = request.POST.get('action', '')
        teacher_id = request.POST.get('teacher_id', '').strip()
        if action == 'add' and teacher_id:
            teacher = get_object_or_404(User, pk=teacher_id)
            ts, created = TeacherSubject.objects.get_or_create(
                teacher=teacher, subject=subject
            )
            if created:
                messages.success(request, f'{teacher.get_full_name()} asignado a «{subject.name}».')
            else:
                messages.warning(request, f'{teacher.get_full_name()} ya tenía esta materia.')
        elif action == 'remove' and teacher_id:
            teacher = get_object_or_404(User, pk=teacher_id)
            TeacherSubject.objects.filter(teacher=teacher, subject=subject).delete()
            messages.success(request, f'{teacher.get_full_name()} quitado de «{subject.name}».')
        return redirect('coordinator:subject_assign', subject_id=subject.pk)

    assigned_ids = subject.teacher_assignments.values_list('teacher_id', flat=True)
    assigned     = all_users.filter(pk__in=assigned_ids)
    available    = all_users.exclude(pk__in=assigned_ids)

    return render(request, 'coordinator/subject_assign.html', {
        'subject':   subject,
        'assigned':  assigned,
        'available': available,
    })


@coordinator_required
def teacher_subjects(request, teacher_id):
    """Ver/gestionar materias asignadas a un docente específico."""
    teacher  = get_object_or_404(User, pk=teacher_id)
    profile, _ = TeacherProfile.objects.get_or_create(user=teacher)
    all_subjects = Subject.objects.filter(active=True)
    assigned_ids = TeacherSubject.objects.filter(
        teacher=teacher
    ).values_list('subject_id', flat=True)
    assigned     = all_subjects.filter(pk__in=assigned_ids)
    available    = all_subjects.exclude(pk__in=assigned_ids)

    if request.method == 'POST':
        action     = request.POST.get('action', '')
        subject_id = request.POST.get('subject_id', '').strip()
        if action == 'add' and subject_id:
            subj = get_object_or_404(Subject, pk=subject_id)
            _, created = TeacherSubject.objects.get_or_create(
                teacher=teacher, subject=subj
            )
            if created:
                messages.success(request, f'Materia «{subj.name}» asignada.')
            else:
                messages.warning(request, 'Ya tenía esa materia.')
        elif action == 'remove' and subject_id:
            subj = get_object_or_404(Subject, pk=subject_id)
            TeacherSubject.objects.filter(teacher=teacher, subject=subj).delete()
            messages.success(request, f'Materia «{subj.name}» removida.')
        return redirect('coordinator:teacher_subjects', teacher_id=teacher.pk)

    return render(request, 'coordinator/teacher_subjects.html', {
        'teacher':   teacher,
        'profile':   profile,
        'assigned':  assigned,
        'available': available,
    })
