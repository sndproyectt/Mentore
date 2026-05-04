from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Q
from datetime import date
from .models import Grade
from students.models import Student, Classroom


def parsear_nota(valor, default=0):
    try:
        v = str(valor).strip()
        if len(v) == 2 and '.' not in v:
            v = v[0] + '.' + v[1]
        return float(v)
    except:
        return float(default)


@login_required
def grade_list(request):
    query = request.GET.get('q', '')
    period = request.GET.get('period', '')
    classroom_id = request.GET.get('classroom', '')
    grades = Grade.objects.filter(student__teacher=request.user)
    if query:
        grades = grades.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(activity_name__icontains=query)
        )
    if period:
        grades = grades.filter(period__icontains=period)
    if classroom_id:
        grades = grades.filter(student__classroom_id=classroom_id)
    avg = grades.aggregate(Avg('score'))['score__avg'] or 0
    classrooms = Classroom.objects.filter(teacher=request.user)
    periods = Grade.objects.filter(student__teacher=request.user).values_list('period', flat=True).distinct()
    return render(request, 'grades/grade_list.html', {
        'grades': grades,
        'avg': round(avg, 2),
        'classrooms': classrooms,
        'periods': [p for p in periods if p],
        'query': query,
        'selected_period': period,
        'selected_classroom': classroom_id,
    })


@login_required
def grade_create(request):
    students = Student.objects.filter(teacher=request.user, active=True)
    preselect = request.GET.get('student', '')
    if request.method == 'POST':
        p = request.POST
        student = get_object_or_404(Student, pk=p.get('student'), teacher=request.user)
        Grade.objects.create(
            student=student,
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
        'students': students,
        'action': 'Registrar',
        'preselect': preselect,
        'today': date.today().isoformat(),
        'grade_types': Grade.GRADE_TYPES,
    })


@login_required
def grade_edit(request, pk):
    grade = get_object_or_404(Grade, pk=pk, student__teacher=request.user)
    students = Student.objects.filter(teacher=request.user, active=True)
    if request.method == 'POST':
        p = request.POST
        grade.activity_name = p.get('activity_name', grade.activity_name)
        grade.grade_type = p.get('grade_type', grade.grade_type)
        grade.score = parsear_nota(p.get('score', grade.score), grade.score)
        grade.max_score = 5.0
        grade.period = p.get('period', grade.period)
        grade.date = p.get('date') or grade.date
        grade.observations = p.get('observations', grade.observations)
        grade.save()
        messages.success(request, 'Nota actualizada correctamente.')
        return redirect('grades:list')
    return render(request, 'grades/grade_form.html', {
        'grade': grade,
        'students': students,
        'action': 'Editar',
        'today': date.today().isoformat(),
        'grade_types': Grade.GRADE_TYPES,
    })


@login_required
def grade_delete(request, pk):
    grade = get_object_or_404(Grade, pk=pk, student__teacher=request.user)
    if request.method == 'POST':
        grade.delete()
        messages.success(request, 'Nota eliminada.')
    return redirect('grades:list')