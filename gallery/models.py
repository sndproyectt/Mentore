from django.db import models
from django.contrib.auth.models import User
from students.models import Student


class WorkCategory(models.Model):
    name = models.CharField(max_length=80)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')

    def __str__(self):
        return self.name


class StudentWork(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='works')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='works')
    category = models.ForeignKey(WorkCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='works')
    title = models.CharField(max_length=200, verbose_name='Título')
    description = models.TextField(blank=True, verbose_name='Descripción')
    image = models.ImageField(upload_to='gallery/', blank=True, null=True)
    file = models.FileField(upload_to='gallery/files/', blank=True, null=True)
    is_public = models.BooleanField(default=True, verbose_name='Visible para padres')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Trabajo'
        verbose_name_plural = 'Trabajos'

    def __str__(self):
        return f"{self.title} — {self.student}"
