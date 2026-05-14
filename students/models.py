from django.db import models
from django.contrib.auth.models import User


class Classroom(models.Model):
    # ── Propietario original (FK) — se mantiene para compatibilidad ──
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='classrooms',
        verbose_name='Docente principal',
    )
    # ── NUEVO: varios docentes por salón ─────────────────────────────
    teachers = models.ManyToManyField(
        User,
        related_name='shared_classrooms',
        blank=True,
        verbose_name='Docentes con acceso',
    )

    name        = models.CharField(max_length=100, verbose_name='Nombre del grupo')
    grade_level = models.CharField(max_length=50,  blank=True, verbose_name='Nivel')
    subject     = models.CharField(max_length=100, blank=True, verbose_name='Materia')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Grupo'
        verbose_name_plural = 'Grupos'

    def __str__(self):
        return self.name

    def student_count(self):
        return self.students.count()

    def all_teachers(self):
        """Devuelve todos los docentes (principal + compartidos) sin duplicados."""
        from django.contrib.auth.models import User
        ids = set(self.teachers.values_list('id', flat=True))
        ids.add(self.teacher_id)
        return User.objects.filter(id__in=ids).order_by('last_name', 'first_name')

    def has_teacher_access(self, user):
        """True si el usuario es docente principal O está en la lista M2M."""
        return self.teacher_id == user.pk or self.teachers.filter(pk=user.pk).exists()


class Student(models.Model):
    GENDER_CHOICES = [('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')]

    teacher   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='students')
    classroom = models.ForeignKey(
        Classroom, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='students'
    )
    first_name   = models.CharField(max_length=80,  verbose_name='Nombre')
    last_name    = models.CharField(max_length=80,  verbose_name='Apellido')
    document_id  = models.CharField(max_length=30,  blank=True, verbose_name='Documento de identidad')
    email        = models.EmailField(blank=True,                 verbose_name='Correo')
    parent_email = models.EmailField(blank=True,                 verbose_name='Correo del padre/madre')
    parent_name  = models.CharField(max_length=120, blank=True, verbose_name='Nombre del acudiente')
    parent_phone = models.CharField(max_length=30,  blank=True, verbose_name='Teléfono del acudiente')
    date_of_birth = models.DateField(null=True, blank=True,     verbose_name='Fecha de nacimiento')
    gender       = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    notes        = models.TextField(blank=True,                 verbose_name='Observaciones')
    photo        = models.ImageField(upload_to='students/', blank=True, null=True)
    active       = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}".upper()

    def average_grade(self):
        grades = self.grades.all()
        if not grades:
            return None
        total = sum(g.score for g in grades)
        return round(total / len(grades), 1)


class Announcement(models.Model):
    PRIORITY_CHOICES = [
        ('low',    'Informativo'),
        ('medium', 'Importante'),
        ('high',   'Urgente'),
    ]
    # Quién lo crea
    teacher  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    # Destinatarios: docentes y/o padres (via estudiante)
    teacher_recipients = models.ManyToManyField(
        User, blank=True,
        related_name='received_announcements',
        verbose_name='Docentes destinatarios',
    )
    student_recipients = models.ManyToManyField(
        'Student', blank=True,
        related_name='received_announcements',
        verbose_name='Estudiantes (para notif. a padres)',
    )
    # FK classroom se mantiene nullable para compatibilidad legacy
    classroom = models.ForeignKey(
        'Classroom', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='announcements', verbose_name='Grupo'
    )
    title    = models.CharField(max_length=200, verbose_name='Título')
    content  = models.TextField(verbose_name='Contenido')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='low', verbose_name='Prioridad')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comunicado'
        verbose_name_plural = 'Comunicados'

    def __str__(self):
        return self.title


class DirectMessage(models.Model):
    """Mensaje interno de docente → docente (no confundir con Message padre-alumno)."""
    sender    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_direct_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_direct_messages')
    subject   = models.CharField(max_length=200, verbose_name='Asunto')
    body      = models.TextField(verbose_name='Mensaje')
    is_read   = models.BooleanField(default=False)
    sent_at   = models.DateTimeField(auto_now_add=True)
    reply_to  = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Mensaje interno'
        verbose_name_plural = 'Mensajes internos'

    def __str__(self):
        return f"{self.sender} → {self.recipient}: {self.subject}"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Presente'),
        ('absent',  'Ausente'),
        ('late',    'Tarde'),
        ('excused', 'Excusa'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    date    = models.DateField(verbose_name='Fecha')
    status  = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    note    = models.CharField(max_length=200, blank=True, verbose_name='Nota')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['student', 'date']
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'

    def __str__(self):
        return f"{self.student} - {self.date} - {self.get_status_display()}"


class Message(models.Model):
    teacher      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_sent')
    student      = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='messages')
    subject      = models.CharField(max_length=200, verbose_name='Asunto')
    body         = models.TextField(verbose_name='Mensaje')
    sent_at      = models.DateTimeField(auto_now_add=True)
    is_read      = models.BooleanField(default=False)
    sender_label = models.CharField(max_length=60, blank=True, default='', verbose_name='Enviado por')
    reply_to     = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'

    def __str__(self):
        return f"Para {self.student} — {self.subject}"


class Guardian(models.Model):
    """Acudiente de un estudiante. Uno obligatorio, hasta 2 opcionales (max 3)."""
    student     = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='guardians')
    name        = models.CharField(max_length=120, verbose_name='Nombre')
    email       = models.EmailField(blank=True,    verbose_name='Correo')
    phone       = models.CharField(max_length=30,  blank=True, verbose_name='Teléfono')
    relationship = models.CharField(max_length=60, blank=True, verbose_name='Parentesco')
    is_primary  = models.BooleanField(default=False, verbose_name='Principal')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'name']
        verbose_name = 'Acudiente'
        verbose_name_plural = 'Acudientes'

    def __str__(self):
        return f"{self.name} ({self.student})"