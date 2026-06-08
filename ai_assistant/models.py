import os

from django.db import models
from django.contrib.auth.models import User


def ai_document_upload_path(instance, filename):
    safe_name = os.path.basename(filename)
    return f'ai_documents/{instance.user_id}/{safe_name}'


def ai_generated_document_path(instance, filename):
    safe_name = os.path.basename(filename)
    return f'ai_generated_documents/{instance.user_id}/{safe_name}'


class ChatDocument(models.Model):
    """Documento subido por el docente para consultar con la IA."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='chat_documents',
    )
    file = models.FileField(upload_to=ai_document_upload_path)
    original_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    extracted_text = models.TextField(blank=True)
    extraction_error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Documento del chat'
        verbose_name_plural = 'Documentos del chat'

    def __str__(self):
        return f'{self.original_name} ({self.user.username})'

    @property
    def extension(self):
        return os.path.splitext(self.original_name)[1].lower()

    @property
    def is_ready(self):
        return bool(self.extracted_text.strip()) and not self.extraction_error


class ChatHistory(models.Model):
    """Historial de mensajes individuales usuario-IA."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_histories')
    user_message = models.TextField()
    ai_response = models.TextField()
    document_context = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Historial de Chat'
        verbose_name_plural = 'Historiales de Chat'

    def __str__(self):
        return f"Chat de {self.user.username} - {self.created_at}"


class AIMessageVersion(models.Model):
    """Versiones conservadas de una respuesta generada por IA."""

    message = models.ForeignKey(
        ChatHistory, on_delete=models.CASCADE, related_name='versions',
    )
    content = models.TextField()
    numero_version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['numero_version']
        unique_together = [('message', 'numero_version')]
        verbose_name = 'Version de respuesta IA'
        verbose_name_plural = 'Versiones de respuestas IA'

    def __str__(self):
        return f"Version {self.numero_version} de mensaje {self.message_id}"


class AIFeedback(models.Model):
    """Feedback humano sobre una respuesta, almacenado para analisis posterior."""

    POSITIVE = 1
    NEGATIVE = -1
    TYPE_CHOICES = [
        (POSITIVE, 'Positivo'),
        (NEGATIVE, 'Negativo'),
    ]

    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='ai_feedback',
    )
    mensaje = models.ForeignKey(
        ChatHistory, on_delete=models.CASCADE, related_name='feedback',
    )
    tipo = models.SmallIntegerField(choices=TYPE_CHOICES)
    fecha = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('usuario', 'mensaje')]
        indexes = [
            models.Index(fields=['mensaje', 'tipo']),
            models.Index(fields=['usuario', 'fecha']),
        ]
        verbose_name = 'Feedback de IA'
        verbose_name_plural = 'Feedback de IA'

    def __str__(self):
        return f"Feedback {self.tipo} de {self.usuario_id} para {self.mensaje_id}"


class AIDownloadLog(models.Model):
    """Registro de descargas de respuestas IA."""

    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='ai_download_logs',
    )
    mensaje = models.ForeignKey(
        ChatHistory, on_delete=models.CASCADE, related_name='download_logs',
    )
    formato = models.CharField(max_length=10)
    filename = models.CharField(max_length=255)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['usuario', 'fecha']),
            models.Index(fields=['mensaje', 'formato']),
        ]
        verbose_name = 'Descarga de respuesta IA'
        verbose_name_plural = 'Descargas de respuestas IA'

    def __str__(self):
        return f"{self.filename} ({self.usuario_id})"


class GeneratedDocument(models.Model):
    """Archivo generado por la IA para descarga desde el chat."""

    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('docx', 'Word'),
        ('xlsx', 'Excel'),
        ('csv', 'CSV'),
        ('txt', 'Texto'),
        ('md', 'Markdown'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_generated_documents')
    file = models.FileField(upload_to=ai_generated_document_path)
    original_name = models.CharField(max_length=255)
    file_format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    file_size = models.PositiveIntegerField(default=0)
    source_prompt = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Documento generado por IA'
        verbose_name_plural = 'Documentos generados por IA'

    def __str__(self):
        return f'{self.original_name} ({self.user.username})'


class GlobalAssistantPreference(models.Model):
    """Preferencias visuales del asistente flotante por usuario."""

    AVATAR_CHOICES = [
        ('avatar_a', 'Avatar normal'),
        ('avatar_b', 'Avatar transparente'),
    ]
    SIZE_CHOICES = [
        ('small', 'Pequeno'),
        ('medium', 'Mediano'),
        ('large', 'Grande'),
        ('xlarge', 'Extra grande'),
    ]
    POSITION_CHOICES = [
        ('bottom_right', 'Inferior derecha'),
        ('bottom_left', 'Inferior izquierda'),
    ]
    BORDER_COLOR_CHOICES = [
        ('mentore_blue', 'Azul Mentore'),
        ('green', 'Verde'),
        ('purple', 'Morado'),
        ('gray', 'Gris'),
        ('black', 'Negro'),
        ('none', 'Sin borde'),
    ]
    SHADOW_CHOICES = [
        ('none', 'Sin sombra'),
        ('soft', 'Sombra suave'),
        ('medium', 'Sombra media'),
        ('intense', 'Sombra intensa'),
    ]
    ACTIVITY_EFFECT_CHOICES = [
        ('halo', 'Halo luminoso'),
        ('glow', 'Brillo pulsante'),
        ('pulse', 'Pulso'),
        ('none', 'Ninguno'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='global_assistant_preference',
    )
    avatar = models.CharField(max_length=40, choices=AVATAR_CHOICES, default='avatar_a')
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, default='medium')
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='bottom_right')
    transparency = models.PositiveSmallIntegerField(default=0)
    border_color = models.CharField(max_length=20, choices=BORDER_COLOR_CHOICES, default='mentore_blue')
    shadow = models.CharField(max_length=20, choices=SHADOW_CHOICES, default='medium')
    animations_enabled = models.BooleanField(default=True)
    activity_effect = models.CharField(max_length=20, choices=ACTIVITY_EFFECT_CHOICES, default='halo')
    is_visible = models.BooleanField(default=True)
    drawer_width = models.PositiveSmallIntegerField(default=520)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Preferencia del asistente global'
        verbose_name_plural = 'Preferencias del asistente global'

    def __str__(self):
        return f'Asistente global de {self.user.username}'


class ConversationSummary(models.Model):
    """
    Memoria media: resumen automático de la conversación generado
    periódicamente por la IA (cada ~10 interacciones).
    Permite mantener contexto sin enviar todos los mensajes al modelo.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversation_summaries')
    summary = models.TextField(help_text="Resumen compacto de la conversación generado por IA")
    messages_covered = models.IntegerField(
        default=0,
        help_text="Cantidad de mensajes cubiertos por este resumen"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Resumen de Conversación'
        verbose_name_plural = 'Resúmenes de Conversación'

    def __str__(self):
        return f"Resumen de {self.user.username} ({self.messages_covered} msgs) - {self.created_at}"


class UserMemory(models.Model):
    """
    Memoria persistente del usuario: información estable sobre el perfil
    pedagógico del docente. Se inyecta automáticamente en cada solicitud.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ai_memory')
    teaching_grade = models.CharField(
        max_length=50, blank=True, default='',
        help_text="Grado(s) que enseña, ej: '3° de primaria'"
    )
    subjects = models.CharField(
        max_length=200, blank=True, default='',
        help_text="Materias que enseña, ej: 'Matemáticas, Lenguaje'"
    )
    teaching_style = models.TextField(
        blank=True, default='',
        help_text="Estilo de enseñanza preferido"
    )
    preferred_activities = models.TextField(
        blank=True, default='',
        help_text="Tipos de actividades que prefiere"
    )
    school_context = models.TextField(
        blank=True, default='',
        help_text="Contexto escolar relevante (rural/urbano, recursos, etc.)"
    )
    additional_notes = models.TextField(
        blank=True, default='',
        help_text="Notas adicionales sobre el perfil pedagógico"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Memoria de Usuario'
        verbose_name_plural = 'Memorias de Usuario'

    def __str__(self):
        return f"Memoria de {self.user.username}"

    def get_profile_context(self):
        """Genera un texto compacto con el perfil del usuario para inyectar al prompt."""
        parts = []
        if self.teaching_grade:
            parts.append(f"Grado que enseña: {self.teaching_grade}")
        if self.subjects:
            parts.append(f"Materias: {self.subjects}")
        if self.teaching_style:
            parts.append(f"Estilo de enseñanza: {self.teaching_style}")
        if self.preferred_activities:
            parts.append(f"Actividades preferidas: {self.preferred_activities}")
        if self.school_context:
            parts.append(f"Contexto escolar: {self.school_context}")
        if self.additional_notes:
            parts.append(f"Notas: {self.additional_notes}")
        return "\n".join(parts) if parts else ""
