from django.db import models
from django.contrib.auth.models import User
from students.models import Student


class Subject(models.Model):
    """Materia académica independiente del sistema."""
    name        = models.CharField(max_length=120, unique=True, verbose_name='Nombre')
    code        = models.CharField(max_length=20, blank=True, verbose_name='Código')
    description = models.TextField(blank=True, verbose_name='Descripción')
    active      = models.BooleanField(default=True, verbose_name='Activa')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Materia'
        verbose_name_plural = 'Materias'

    def __str__(self):
        return self.name


class TeacherSubject(models.Model):
    """Asignación de una materia a un docente."""
    teacher  = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='teacher_subjects',
        verbose_name='Docente',
    )
    subject  = models.ForeignKey(
        Subject, on_delete=models.CASCADE,
        related_name='teacher_assignments',
        verbose_name='Materia',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('teacher', 'subject')
        ordering = ['subject__name']
        verbose_name = 'Materia asignada'
        verbose_name_plural = 'Materias asignadas'

    def __str__(self):
        return f"{self.teacher.get_full_name()} → {self.subject.name}"


class Grade(models.Model):
    GRADE_TYPES = [
        ('exam',          'Examen'),
        ('quiz',          'Quiz'),
        ('homework',      'Tarea'),
        ('workshop',      'Taller'),
        ('project',       'Proyecto'),
        ('participation', 'Participación'),
        ('activity',      'Actividad'),
        ('other',         'Otro'),
    ]
    PERIOD_CHOICES = [
        ('Periodo I', 'Periodo I'),
        ('Periodo II', 'Periodo II'),
        ('Periodo III', 'Periodo III'),
    ]
    SCALE = [
        ('grade-d', 'Bajo', 0.0, 3.4, '#991B1B'),
        ('grade-c', 'Básico', 3.5, 4.0, '#92400E'),
        ('grade-b', 'Alto', 4.1, 4.7, '#1E40AF'),
        ('grade-a', 'Superior', 4.8, 5.0, '#065F46'),
    ]

    student       = models.ForeignKey(
        Student, on_delete=models.CASCADE,
        related_name='grades', verbose_name='Estudiante',
    )
    subject       = models.ForeignKey(
        Subject, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='grades', verbose_name='Materia',
    )
    # Campo legacy de texto — se mantiene para compatibilidad con datos existentes
    subject_text  = models.CharField(
        max_length=100, blank=True,
        verbose_name='Materia (texto)',
        help_text='Solo para datos migrados. Usa el campo Materia (FK).',
    )
    activity_name = models.CharField(max_length=200, verbose_name='Nombre de la actividad')
    grade_type    = models.CharField(
        max_length=20, choices=GRADE_TYPES,
        default='activity', verbose_name='Tipo',
    )
    score         = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name='Nota',
    )
    max_score     = models.DecimalField(
        max_digits=4, decimal_places=2,
        default=5.0, verbose_name='Nota máxima',
    )
    period        = models.CharField(
        max_length=50, blank=True, choices=PERIOD_CHOICES, verbose_name='Periodo',
    )
    date          = models.DateField(verbose_name='Fecha')
    observations  = models.TextField(blank=True, verbose_name='Observaciones')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Nota'
        verbose_name_plural = 'Notas'

    def __str__(self):
        subj = self.subject.name if self.subject else (self.subject_text or '—')
        return f"{self.student} [{subj}] {self.activity_name}: {self.score}"

    def percentage(self):
        if self.max_score:
            return round((float(self.score) / float(self.max_score)) * 100, 1)
        return 0

    @classmethod
    def scale_for_score(cls, score):
        try:
            value = round(float(score), 2)
        except (TypeError, ValueError):
            return None
        for css_class, label, minimum, maximum, color in cls.SCALE:
            if minimum <= value <= maximum:
                return {
                    'class': css_class,
                    'label': label,
                    'min': minimum,
                    'max': maximum,
                    'color': color,
                }
        return None

    def scale_label(self):
        scale = self.scale_for_score(self.score)
        return scale['label'] if scale else ''

    def scale_class(self):
        scale = self.scale_for_score(self.score)
        return scale['class'] if scale else ''

    def subject_display(self):
        """Nombre de la materia independientemente de si es FK o texto."""
        if self.subject:
            return self.subject.name
        return self.subject_text or '—'
