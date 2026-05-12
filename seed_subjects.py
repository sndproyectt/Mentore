"""
Script de inicialización de materias y asignación a docentes — Mentore
Uso: python manage.py shell < seed_subjects.py

Crea las 3 materias iniciales y las asigna a los docentes registrados.
Si ya existen, no las duplica.
"""
from django.contrib.auth.models import User
from grades.models import Subject, TeacherSubject, Grade

# ── 1. Crear materias iniciales ───────────────────────────────

INITIAL_SUBJECTS = [
    {"name": "Fraternos y espirituales", "code": "FRE", "description": "Formación en valores fraternales y espirituales."},
    {"name": "Pilosos",                  "code": "PIL", "description": "Habilidades prácticas y de cuidado personal."},
    {"name": "Comunicativos",            "code": "COM", "description": "Competencias comunicativas orales y escritas."},
]

created_subjects = []
for data in INITIAL_SUBJECTS:
    subj, created = Subject.objects.get_or_create(
        name=data["name"],
        defaults={"code": data["code"], "description": data["description"], "active": True}
    )
    created_subjects.append(subj)
    if created:
        print(f"  ✅ Materia creada: {subj.name}")
    else:
        print(f"  ⚠️  Ya existía: {subj.name}")

# ── 2. Asignar materias a docentes ────────────────────────────

teachers = User.objects.filter(teacher_profile__role='teacher').select_related('teacher_profile')
print(f"\n  Docentes encontrados: {teachers.count()}")

for i, teacher in enumerate(teachers):
    # Asignar materias distribuidas (round-robin)
    subj = created_subjects[i % len(created_subjects)]
    ts, created = TeacherSubject.objects.get_or_create(teacher=teacher, subject=subj)
    if created:
        print(f"  ✅ {teacher.get_full_name()} → {subj.name}")
    else:
        print(f"  ⚠️  {teacher.get_full_name()} ya tenía: {subj.name}")

# ── 3. Migrar notas legacy (subject_text → subject FK) ───────

legacy = Grade.objects.filter(subject__isnull=True).exclude(subject_text='')
print(f"\n  Notas legacy sin FK: {legacy.count()}")
migrated = 0
for grade in legacy:
    match = Subject.objects.filter(name__iexact=grade.subject_text.strip()).first()
    if match:
        grade.subject = match
        grade.save(update_fields=['subject'])
        migrated += 1

print(f"  ✅ Migradas al FK: {migrated}")

# ── 4. Resumen ────────────────────────────────────────────────

print()
print("=" * 50)
print(f"  Materias en el sistema : {Subject.objects.count()}")
print(f"  Asignaciones docente→materia: {TeacherSubject.objects.count()}")
print(f"  Notas con materia FK  : {Grade.objects.filter(subject__isnull=False).count()}")
print(f"  Notas sin materia     : {Grade.objects.filter(subject__isnull=True).count()}")
print("=" * 50)
print("Inicialización completada. Ejecuta ahora:")
print("  python manage.py migrate")