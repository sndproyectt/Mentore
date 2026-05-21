from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import StudentWork, WorkCategory
from students.models import Student, Classroom
from django.db.models import Q


@login_required
def gallery_list(request):
    query = request.GET.get('q', '')
    cat_id = request.GET.get('cat', '')
    _role = getattr(getattr(request.user, 'teacher_profile', None), 'role', 'teacher')
    if _role == 'coordinator':
        works = StudentWork.objects.select_related('teacher', 'student')
    else:
        accessible_ids = _accessible_students(request.user).values_list('id', flat=True)
        works = StudentWork.objects.filter(
            Q(teacher=request.user) | Q(student_id__in=accessible_ids)
        ).distinct()
    if query:
        works = works.filter(Q(title__icontains=query) | Q(student__first_name__icontains=query) | Q(student__last_name__icontains=query))
    if cat_id:
        works = works.filter(category_id=cat_id)
    categories = WorkCategory.objects.filter(teacher=request.user)
    return render(request, 'gallery/gallery_list.html', {'works': works, 'query': query, 'categories': categories})


def _accessible_students(user):
    """Estudiantes a los que el docente tiene acceso (propio + salones compartidos)."""
    _role = getattr(getattr(user, 'teacher_profile', None), 'role', 'teacher')
    if _role == 'coordinator':
        return Student.objects.filter(active=True)
    shared_cr_ids = Classroom.objects.filter(
        Q(teacher=user) | Q(teachers=user)
    ).values_list('id', flat=True)
    return Student.objects.filter(
        Q(teacher=user) | Q(classroom_id__in=shared_cr_ids),
        active=True,
    ).distinct()


@login_required
def work_upload(request):
    students = _accessible_students(request.user).select_related('classroom').order_by('last_name')
    categories = WorkCategory.objects.filter(teacher=request.user)
    if request.method == 'POST':
        p = request.POST
        # Verify the student is accessible to this user
        student = get_object_or_404(Student, pk=p.get('student'))
        if not _accessible_students(request.user).filter(pk=student.pk).exists():
            messages.error(request, 'No tienes acceso a ese estudiante.')
            return redirect('gallery:upload')
        cat_id = p.get('category') or None
        work = StudentWork(
            teacher=request.user,
            student=student,
            title=p.get('title', ''),
            description=p.get('description', ''),
            is_public=p.get('is_public') == 'on',
            category_id=cat_id,
        )
        if 'image' in request.FILES:
            work.image = request.FILES['image']
        if 'file' in request.FILES:
            work.file = request.FILES['file']
        work.save()

        # Handle new category
        new_cat = p.get('new_category', '').strip()
        if new_cat:
            cat, _ = WorkCategory.objects.get_or_create(name=new_cat, teacher=request.user)
            work.category = cat
            work.save()

        messages.success(request, 'Trabajo subido exitosamente a la galería.')
        return redirect('gallery:list')
    return render(request, 'gallery/work_upload.html', {'students': students, 'categories': categories})


@login_required
def work_detail(request, pk):
    work = get_object_or_404(StudentWork, pk=pk, teacher=request.user)
    return render(request, 'gallery/work_detail.html', {'work': work})


@login_required
def work_delete(request, pk):
    work = get_object_or_404(StudentWork, pk=pk, teacher=request.user)
    if request.method == 'POST':
        work.delete()
        messages.success(request, 'Trabajo eliminado.')
    return redirect('gallery:list')


def parent_gallery(request):
    """Public gallery for parents - accessible by parent email query."""
    email = request.GET.get('email', '').strip()
    works = []
    student = None
    if email:
        try:
            student_obj = Student.objects.filter(parent_email__iexact=email, active=True).first()
            if student_obj:
                student = student_obj
                works = StudentWork.objects.filter(student=student_obj, is_public=True)
        except Exception:
            pass
    return render(request, 'gallery/parent_gallery.html', {'works': works, 'student': student, 'email': email})