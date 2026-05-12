"""
Script de datos de demostración — Mentore
Uso: python manage.py shell < seed_demo_data.py

IMPORTANTE: ejecutar DESPUÉS de migrate y seed_subjects.py
"""
import random
from datetime import date, timedelta
from django.contrib.auth.models import User
from django.db.models import Q
from students.models import Student, Classroom
from grades.models import Grade, Subject, TeacherSubject

random.seed(42)

# ── Materias ──────────────────────────────────────────────────
SUBJECTS = list(Subject.objects.filter(active=True))
if not SUBJECTS:
    print("❌ No hay materias. Ejecuta primero seed_subjects.py")
    raise SystemExit

print(f"✅ Materias encontradas: {[s.name for s in SUBJECTS]}")

# ── Actividades por materia ───────────────────────────────────
ACTIVITIES = {
    subj.name: [
        (f"Taller 1 — {subj.name}",     "activity",      "Periodo 1", date(2025, 2, 14)),
        (f"Quiz 1 — {subj.name}",       "quiz",          "Periodo 1", date(2025, 2, 28)),
        (f"Examen P1 — {subj.name}",    "exam",          "Periodo 1", date(2025, 3, 21)),
        (f"Proyecto — {subj.name}",     "project",       "Periodo 1", date(2025, 4,  4)),
        (f"Participación P1",           "participation", "Periodo 1", date(2025, 4, 11)),
        (f"Taller 2 — {subj.name}",     "activity",      "Periodo 2", date(2025, 4, 25)),
        (f"Quiz 2 — {subj.name}",       "quiz",          "Periodo 2", date(2025, 5,  2)),
        (f"Examen P2 — {subj.name}",    "exam",          "Periodo 2", date(2025, 5, 30)),
    ]
    for subj in SUBJECTS
}

# ── Procesar todos los salones con estudiantes ────────────────
classrooms = Classroom.objects.prefetch_related('students').all()
total_created = 0
total_skipped = 0

for classroom in classrooms:
    students = list(classroom.students.filter(active=True))
    if not students:
        print(f"  ⚠️  Salón {classroom.name}: sin estudiantes")
        continue

    print(f"\n  📚 Salón: {classroom.name} — {len(students)} estudiantes")

    for student in students:
        base = random.uniform(2.8, 5.0)

        for subj in SUBJECTS:
            activities = ACTIVITIES.get(subj.name, [])
            for act_name, act_type, period, act_date in activities:
                if Grade.objects.filter(
                    student=student,
                    subject=subj,
                    activity_name=act_name
                ).exists():
                    total_skipped += 1
                    continue
                variation = random.uniform(-1.0, 0.6)
                score     = round(min(5.0, max(1.0, base + variation)), 1)
                Grade.objects.create(
                    student=student,
                    subject=subj,
                    subject_text=subj.name,
                    activity_name=act_name,
                    grade_type=act_type,
                    score=score,
                    max_score=5.0,
                    period=period,
                    date=act_date,
                    observations="",
                )
                total_created += 1

# ── Resumen ───────────────────────────────────────────────────
print()
print("=" * 55)
print(f"  Salones procesados  : {classrooms.count()}")
print(f"  Notas creadas       : {total_created}")
print(f"  Notas ya existentes : {total_skipped}")
print(f"  Total notas en BD   : {Grade.objects.count()}")
print("=" * 55)
print("Datos de demo generados correctamente.")