"""
Vistas del módulo de notas — Mentore.
- Docentes ven notas de sus estudiantes accesibles (FK + M2M).
- Solo pueden crear/editar/eliminar notas de sus materias asignadas.
- El coordinador puede editar cualquier nota.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Q
from datetime import date

from .models import Grade, Subject, TeacherSubject
from students.models import Student, Classroom


# ── Helpers ───────────────────────────────────────────────────────────────────

def parsear_nota(valor, default=0):
    try:
        v = str(valor).strip().replace(',', '.')
        if len(v) == 2 and '.' not in v and v.isdigit():
            v = v[0] + '.' + v[1]
        return max(0.0, min(5.0, float(v)))
    except Exception:
        return float(default)


def _accessible_students(user):
    """Estudiantes accesibles: propios (FK) + en salones M2M."""
    shared_ids = user.shared_classrooms.values_list('id', flat=True)
    return Student.objects.filter(
        Q(teacher=user) | Q(classroom_id__in=shared_ids)
    ).distinct()


def _accessible_classrooms(user):
    return Classroom.objects.filter(
        Q(teacher=user) | Q(teachers=user)
    ).distinct()


def _my_subjects(user):
    """Materias (Subject FK) asignadas al docente."""
    return Subject.objects.filter(teacher_assignments__teacher=user)


def _can_edit_grade(user, grade):
    """
    True si el usuario puede editar/eliminar esta nota:
    - Es coordinador, O
    - Tiene la materia asignada (y acceso al estudiante)
    """
    from accounts.models import TeacherProfile
    try:
        profile = user.teacher_profile
        if profile.role == 'coordinator':
            return True
    except Exception:
        pass
    if grade.subject:
        return TeacherSubject.objects.filter(
            teacher=user, subject=grade.subject
        ).exists()
    return True   # notas sin materia → editable por quien tenga acceso


# ── Vistas ────────────────────────────────────────────────────────────────────

@login_required
def grade_list(request):
    from accounts.models import TeacherProfile

    is_coord = False
    try:
        is_coord = request.user.teacher_profile.role == 'coordinator'
    except Exception:
        pass

    query        = request.GET.get('q', '')
    period       = request.GET.get('period', '')
    classroom_id = request.GET.get('classroom', '')
    subject_id   = request.GET.get('subject', '')

    if is_coord:
        # Coordinador ve TODO
        student_ids = Student.objects.filter(active=True).values_list('id', flat=True)
        classrooms  = Classroom.objects.all().order_by('name')
    else:
        student_ids = _accessible_students(request.user).values_list('id', flat=True)
        classrooms  = _accessible_classrooms(request.user)

    grades = Grade.objects.filter(
        student_id__in=student_ids
    ).select_related('student', 'subject', 'student__classroom')

    if query:
        grades = grades.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query)  |
            Q(activity_name__icontains=query)
        )
    if period:
        grades = grades.filter(period__icontains=period)
    if classroom_id:
        grades = grades.filter(student__classroom_id=classroom_id)
    if subject_id:
        grades = grades.filter(subject_id=subject_id)

    avg      = grades.aggregate(Avg('score'))['score__avg'] or 0
    subjects = Subject.objects.filter(active=True)
    periods  = Grade.objects.filter(
        student_id__in=student_ids
    ).values_list('period', flat=True).distinct()

    my_subjects = _my_subjects(request.user) if not is_coord else None

    return render(request, 'grades/grade_list.html', {
        'grades':             grades,
        'avg':                round(float(avg), 2),
        'classrooms':         classrooms,
        'subjects':           subjects,
        'periods':            [p for p in periods if p],
        'query':              query,
        'selected_period':    period,
        'selected_classroom': classroom_id,
        'selected_subject':   subject_id,
        'my_subjects':        my_subjects,
        'is_coord':           is_coord,
    })


@login_required
def grade_create(request):
    from accounts.models import TeacherProfile

    is_coord = False
    try:
        is_coord = request.user.teacher_profile.role == 'coordinator'
    except Exception:
        pass

    if is_coord:
        students       = Student.objects.filter(active=True).order_by('last_name', 'first_name')
        avail_subjects = Subject.objects.filter(active=True)
    else:
        students       = _accessible_students(request.user).filter(active=True).order_by('last_name', 'first_name')
        avail_subjects = _my_subjects(request.user).filter(active=True)

    preselect = request.GET.get('student', '')

    if request.method == 'POST':
        p          = request.POST
        student_pk = p.get('student')
        subject_pk = p.get('subject')

        # Validar acceso al estudiante
        if is_coord:
            student = get_object_or_404(Student, pk=student_pk, active=True)
        else:
            accessible = _accessible_students(request.user).values_list('id', flat=True)
            student    = get_object_or_404(Student, pk=student_pk, id__in=accessible)

        # Validar que tenga la materia asignada
        subject_obj = None
        if subject_pk:
            subject_obj = get_object_or_404(Subject, pk=subject_pk)
            if not is_coord and not TeacherSubject.objects.filter(
                teacher=request.user, subject=subject_obj
            ).exists():
                messages.error(request, f'No tienes asignada la materia «{subject_obj.name}».')
                return redirect('grades:create')

        Grade.objects.create(
            student=student,
            subject=subject_obj,
            subject_text=subject_obj.name if subject_obj else '',
            activity_name=p.get('activity_name', ''),
            grade_type=p.get('grade_type', 'activity'),
            score=parsear_nota(p.get('score', 0)),
            max_score=5.0,
            period=p.get('period', ''),
            date=p.get('date') or date.today(),
            observations=p.get('observations', ''),
        )
        messages.success(request, 'Nota registrada correctamente.')
        return redirect('grades:list')

    return render(request, 'grades/grade_form.html', {
        'students':       students,
        'avail_subjects': avail_subjects,
        'action':         'Registrar',
        'preselect':      preselect,
        'today':          date.today().isoformat(),
        'grade_types':    Grade.GRADE_TYPES,
        'is_coord':       is_coord,
    })


@login_required
def grade_edit(request, pk):
    from accounts.models import TeacherProfile

    is_coord = False
    try:
        is_coord = request.user.teacher_profile.role == 'coordinator'
    except Exception:
        pass

    if is_coord:
        grade = get_object_or_404(Grade, pk=pk)
        students       = Student.objects.filter(active=True).order_by('last_name', 'first_name')
        avail_subjects = Subject.objects.filter(active=True)
    else:
        accessible = _accessible_students(request.user).values_list('id', flat=True)
        grade      = get_object_or_404(Grade, pk=pk, student_id__in=accessible)
        students   = _accessible_students(request.user).filter(active=True).order_by('last_name', 'first_name')
        avail_subjects = _my_subjects(request.user).filter(active=True)

    if not _can_edit_grade(request.user, grade):
        subj_name = grade.subject.name if grade.subject else grade.subject_text
        messages.error(request, f'Solo puedes editar notas de tus materias asignadas. Esta nota es de «{subj_name}».')
        return redirect('grades:list')

    if request.method == 'POST':
        p          = request.POST
        subject_pk = p.get('subject')
        subject_obj = None
        if subject_pk:
            subject_obj = get_object_or_404(Subject, pk=subject_pk)
            if not is_coord and not TeacherSubject.objects.filter(
                teacher=request.user, subject=subject_obj
            ).exists():
                messages.error(request, f'No tienes asignada la materia «{subject_obj.name}».')
                return redirect('grades:list')

        grade.subject        = subject_obj
        grade.subject_text   = subject_obj.name if subject_obj else grade.subject_text
        grade.activity_name  = p.get('activity_name', grade.activity_name)
        grade.grade_type     = p.get('grade_type', grade.grade_type)
        grade.score          = parsear_nota(p.get('score', grade.score), grade.score)
        grade.period         = p.get('period', grade.period)
        grade.date           = p.get('date') or grade.date
        grade.observations   = p.get('observations', grade.observations)
        grade.save()
        messages.success(request, 'Nota actualizada correctamente.')
        return redirect('grades:list')

    return render(request, 'grades/grade_form.html', {
        'grade':          grade,
        'students':       students,
        'avail_subjects': avail_subjects,
        'action':         'Editar',
        'today':          date.today().isoformat(),
        'grade_types':    Grade.GRADE_TYPES,
        'is_coord':       is_coord,
    })


@login_required
def grade_delete(request, pk):
    from accounts.models import TeacherProfile

    is_coord = False
    try:
        is_coord = request.user.teacher_profile.role == 'coordinator'
    except Exception:
        pass

    if is_coord:
        grade = get_object_or_404(Grade, pk=pk)
    else:
        accessible = _accessible_students(request.user).values_list('id', flat=True)
        grade      = get_object_or_404(Grade, pk=pk, student_id__in=accessible)

    if not _can_edit_grade(request.user, grade):
        messages.error(request, 'No tienes permiso para eliminar esta nota.')
        return redirect('grades:list')

    if request.method == 'POST':
        grade.delete()
        messages.success(request, 'Nota eliminada.')
    return redirect('grades:list')


@login_required
def student_grades(request, student_pk):
    """
    Vista de notas agrupadas por materia para un estudiante.
    Accesible por docentes con acceso al estudiante y por el coordinador.
    """
    from accounts.models import TeacherProfile

    is_coord = False
    try:
        is_coord = request.user.teacher_profile.role == 'coordinator'
    except Exception:
        pass

    if is_coord:
        student = get_object_or_404(Student, pk=student_pk)
    else:
        accessible = _accessible_students(request.user).values_list('id', flat=True)
        student    = get_object_or_404(Student, pk=student_pk, id__in=accessible)

    # Agrupar notas por materia
    all_grades    = student.grades.select_related('subject').order_by('subject__name', '-date')
    subjects_data = []
    seen_subjects = {}

    for grade in all_grades:
        key = grade.subject_id if grade.subject else f'txt_{grade.subject_text}'
        if key not in seen_subjects:
            seen_subjects[key] = {
                'subject':     grade.subject,
                'subject_name': grade.subject_display(),
                'grades':      [],
            }
        seen_subjects[key]['grades'].append(grade)

    for key, data in seen_subjects.items():
        grades_list = data['grades']
        if grades_list:
            avg = sum(float(g.score) for g in grades_list) / len(grades_list)
            data['average'] = round(avg, 2)
        else:
            data['average'] = None
        subjects_data.append(data)

    # Promedio general
    all_scores = [float(g.score) for g in all_grades]
    general_avg = round(sum(all_scores) / len(all_scores), 2) if all_scores else None

    return render(request, 'grades/student_grades.html', {
        'student':       student,
        'subjects_data': subjects_data,
        'general_avg':   general_avg,
        'is_coord':      is_coord,
    })
