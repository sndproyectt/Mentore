"""Consultas academicas seguras usando exclusivamente Django ORM.

Este modulo no recibe SQL ni expresiones arbitrarias del modelo. Todas las
consultas son funciones cerradas, validadas y de solo lectura.
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q

from grades.models import Grade, Subject, TeacherSubject
from students.models import Attendance, Classroom, Student

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def _role_for(user):
    try:
        return user.teacher_profile.role
    except Exception:
        return 'teacher'


def _is_coordinator(user):
    return _role_for(user) == 'coordinator' or user.is_superuser


def _limit(value, default=DEFAULT_LIMIT):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, MAX_LIMIT))


def _clean(value):
    if value is None:
        return ''
    return str(value).strip()


def _as_float(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return round(float(value), 2)
    return round(float(value), 2)


def accessible_classrooms(user):
    qs = Classroom.objects.select_related('teacher').prefetch_related('teachers')
    if _is_coordinator(user):
        return qs
    return qs.filter(Q(teacher=user) | Q(teachers=user)).distinct()


def accessible_students(user):
    qs = Student.objects.select_related('classroom', 'teacher').filter(active=True)
    if _is_coordinator(user):
        return qs
    classrooms = accessible_classrooms(user)
    return qs.filter(Q(teacher=user) | Q(classroom__in=classrooms)).distinct()


def accessible_grades(user):
    return Grade.objects.select_related('student', 'student__classroom', 'subject').filter(
        student__in=accessible_students(user)
    )


def accessible_attendance(user):
    return Attendance.objects.select_related('student', 'student__classroom').filter(
        student__in=accessible_students(user)
    )


def _filter_students(qs, grade=None, classroom=None):
    grade = _clean(grade)
    classroom = _clean(classroom)
    if grade:
        qs = qs.filter(
            Q(classroom__grade_level__icontains=grade)
            | Q(classroom__name__icontains=grade)
        )
    if classroom:
        qs = qs.filter(classroom__name__icontains=classroom)
    return qs


def _filter_grades(qs, subject=None, grade=None, classroom=None, activity=None):
    subject = _clean(subject)
    if subject:
        qs = qs.filter(
            Q(subject__name__icontains=subject)
            | Q(subject_text__icontains=subject)
        )
    activity = _clean(activity)
    if activity:
        qs = qs.filter(activity_name__icontains=activity)
    if grade or classroom:
        students = _filter_students(accessible_students_from_grades(qs), grade, classroom)
        qs = qs.filter(student__in=students)
    return qs


def accessible_students_from_grades(grades_qs):
    return Student.objects.filter(pk__in=grades_qs.values('student_id'))


def find_students(user, name=None, grade=None, classroom=None, limit=10):
    qs = _filter_students(accessible_students(user), grade, classroom)
    name = _clean(name)
    if name:
        for token in [part for part in name.split() if part]:
            qs = qs.filter(Q(first_name__icontains=token) | Q(last_name__icontains=token))
    return list(qs.order_by('last_name', 'first_name')[:_limit(limit, 10)])


def serialize_student(student, include_average=False, include_contact=False):
    data = {
        'id': student.pk,
        'name': student.get_full_name(),
        'classroom': student.classroom.name if student.classroom else None,
        'grade_level': student.classroom.grade_level if student.classroom else None,
        'active': student.active,
    }
    if include_contact:
        data.update({
            'email': student.email or None,
            'parent_name': student.parent_name or None,
            'parent_email': student.parent_email or None,
        })
    if include_average:
        data['average'] = _as_float(
            student.grades.aggregate(avg=Avg('score'))['avg']
        )
    return data


def list_students(user, grade=None, classroom=None, limit=DEFAULT_LIMIT):
    students = find_students(user, grade=grade, classroom=classroom, limit=limit)
    return {
        'count': len(students),
        'students': [serialize_student(student) for student in students],
    }


def count_students(user, grade=None, classroom=None):
    qs = _filter_students(accessible_students(user), grade, classroom)
    return {'count': qs.count(), 'grade': _clean(grade) or None, 'classroom': _clean(classroom) or None}


def student_detail(user, student_name):
    matches = find_students(user, student_name, limit=5)
    if not matches:
        return {'found': False, 'matches': []}
    if len(matches) > 1:
        return {'found': False, 'ambiguous': True, 'matches': [serialize_student(s) for s in matches]}
    student = matches[0]
    grade_count = student.grades.count()
    attendance_count = student.attendances.count()
    return {
        'found': True,
        'student': serialize_student(student, include_average=True, include_contact=True),
        'grade_count': grade_count,
        'attendance_count': attendance_count,
    }


def _student_for_action(user, student_name):
    if not _clean(student_name):
        return None, {'found': False, 'missing_parameter': 'student', 'matches': []}
    matches = find_students(user, student_name, limit=5)
    if not matches:
        return None, {'found': False, 'matches': []}
    if len(matches) > 1:
        return None, {'found': False, 'ambiguous': True, 'matches': [serialize_student(s) for s in matches]}
    return matches[0], None


def serialize_grade(grade):
    return {
        'student': grade.student.get_full_name(),
        'subject': grade.subject_display(),
        'activity': grade.activity_name,
        'type': grade.get_grade_type_display(),
        'score': _as_float(grade.score),
        'max_score': _as_float(grade.max_score),
        'period': grade.period,
        'date': grade.date.isoformat() if grade.date else None,
    }


def student_grades(user, student_name, subject=None, limit=DEFAULT_LIMIT, activity=None):
    student = None
    if _clean(student_name):
        student, error = _student_for_action(user, student_name)
        if error:
            return error
    elif not _clean(activity):
        return {'found': False, 'missing_parameter': 'student', 'matches': []}
    qs = accessible_grades(user)
    if student:
        qs = qs.filter(student=student)
    qs = _filter_grades(qs, subject=subject, activity=activity)
    grades = list(qs.order_by('-date')[:_limit(limit)])
    return {
        'found': True,
        'student': serialize_student(student) if student else None,
        'subject': _clean(subject) or None,
        'activity': _clean(activity) or None,
        'count': qs.count(),
        'grades': [serialize_grade(grade) for grade in grades],
    }


def student_average(user, student_name, subject=None):
    student, error = _student_for_action(user, student_name)
    if error:
        return error
    qs = accessible_grades(user).filter(student=student)
    qs = _filter_grades(qs, subject=subject)
    stats = qs.aggregate(avg=Avg('score'), count=Count('id'))
    return {
        'found': True,
        'student': serialize_student(student),
        'subject': _clean(subject) or None,
        'average': _as_float(stats['avg']),
        'grade_count': stats['count'],
    }


def count_grades(user, student_name=None, subject=None):
    qs = accessible_grades(user)
    student_data = None
    if _clean(student_name):
        student, error = _student_for_action(user, student_name)
        if error:
            return error
        student_data = serialize_student(student)
        qs = qs.filter(student=student)
    qs = _filter_grades(qs, subject=subject)
    return {'count': qs.count(), 'student': student_data, 'subject': _clean(subject) or None}


def subject_average(user, subject=None, grade=None, classroom=None):
    qs = _filter_grades(accessible_grades(user), subject=subject, grade=grade, classroom=classroom)
    stats = qs.aggregate(avg=Avg('score'), count=Count('id'))
    return {
        'subject': _clean(subject) or None,
        'grade': _clean(grade) or None,
        'classroom': _clean(classroom) or None,
        'average': _as_float(stats['avg']),
        'grade_count': stats['count'],
    }


def top_students(user, subject=None, grade=None, classroom=None, limit=10):
    students = _filter_students(accessible_students(user), grade, classroom)
    grades = _filter_grades(accessible_grades(user), subject=subject)
    rows = (
        students.filter(grades__in=grades)
        .annotate(average=Avg('grades__score'), grade_count=Count('grades'))
        .filter(grade_count__gt=0)
        .order_by('-average', 'last_name', 'first_name')[:_limit(limit, 10)]
    )
    return {
        'subject': _clean(subject) or None,
        'students': [
            {**serialize_student(student), 'average': _as_float(student.average), 'grade_count': student.grade_count}
            for student in rows
        ],
    }


def low_average_students(user, threshold=3.0, subject=None, grade=None, classroom=None, limit=DEFAULT_LIMIT):
    try:
        threshold = float(threshold)
    except (TypeError, ValueError):
        threshold = 3.0
    students = _filter_students(accessible_students(user), grade, classroom)
    grades = _filter_grades(accessible_grades(user), subject=subject)
    rows = (
        students.filter(grades__in=grades)
        .annotate(average=Avg('grades__score'), grade_count=Count('grades'))
        .filter(average__lt=threshold, grade_count__gt=0)
        .order_by('average', 'last_name', 'first_name')[:_limit(limit)]
    )
    return {
        'threshold': threshold,
        'subject': _clean(subject) or None,
        'students': [
            {**serialize_student(student), 'average': _as_float(student.average), 'grade_count': student.grade_count}
            for student in rows
        ],
    }


def list_classrooms(user, limit=DEFAULT_LIMIT):
    classrooms = list(accessible_classrooms(user).order_by('name')[:_limit(limit)])
    return {
        'count': len(classrooms),
        'classrooms': [
            {
                'id': classroom.pk,
                'name': classroom.name,
                'grade_level': classroom.grade_level,
                'subject': classroom.subject,
                'student_count': classroom.students.filter(active=True).count(),
            }
            for classroom in classrooms
        ],
    }


def list_subjects(user, limit=DEFAULT_LIMIT):
    if _is_coordinator(user):
        qs = Subject.objects.filter(active=True)
    else:
        assigned = TeacherSubject.objects.filter(teacher=user).values('subject_id')
        used = accessible_grades(user).values('subject_id')
        qs = Subject.objects.filter(Q(pk__in=assigned) | Q(pk__in=used), active=True).distinct()
    subjects = list(qs.order_by('name')[:_limit(limit)])
    return {
        'count': len(subjects),
        'subjects': [{'id': subject.pk, 'name': subject.name, 'code': subject.code} for subject in subjects],
    }


def attendance_summary(user, student_name=None, status=None, date_from=None, date_to=None):
    qs = accessible_attendance(user)
    student_data = None
    if _clean(student_name):
        student, error = _student_for_action(user, student_name)
        if error:
            return error
        student_data = serialize_student(student)
        qs = qs.filter(student=student)
    status = _clean(status)
    if status:
        qs = qs.filter(status=status)
    for value, lookup in ((date_from, 'date__gte'), (date_to, 'date__lte')):
        value = _clean(value)
        if value:
            try:
                parsed = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                continue
            qs = qs.filter(**{lookup: parsed})
    by_status = qs.values('status').annotate(count=Count('id')).order_by('status')
    return {
        'student': student_data,
        'count': qs.count(),
        'by_status': list(by_status),
    }
