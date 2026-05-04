from django.db import models
from students.models import Student


class Grade(models.Model):
    GRADE_TYPES = [
        ('exam', 'Examen'),
        ('quiz', 'Quiz'),
        ('homework', 'Tarea'),
        ('project', 'Proyecto'),
        ('participation', 'Participación'),
        ('activity', 'Actividad'),
        ('other', 'Otro'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades')
    activity_name = models.CharField(max_length=200, verbose_name='Nombre de la actividad')
    grade_type = models.CharField(max_length=20, choices=GRADE_TYPES, default='activity', verbose_name='Tipo')
    score = models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Nota')
    max_score = models.DecimalField(max_digits=4, decimal_places=2, default=5.0, verbose_name='Nota máxima')
    period = models.CharField(max_length=50, blank=True, verbose_name='Periodo')
    date = models.DateField(verbose_name='Fecha')
    observations = models.TextField(blank=True, verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Nota'
        verbose_name_plural = 'Notas'

    def __str__(self):
        return f"{self.student} - {self.activity_name}: {self.score}"

    def percentage(self):
        if self.max_score:
            return round((self.score / self.max_score) * 100, 1)
        return 0
