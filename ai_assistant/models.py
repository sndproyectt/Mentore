from django.db import models
from django.contrib.auth.models import User


class ChatHistory(models.Model):
    """Historial de mensajes individuales usuario-IA."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_histories')
    user_message = models.TextField()
    ai_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Historial de Chat'
        verbose_name_plural = 'Historiales de Chat'

    def __str__(self):
        return f"Chat de {self.user.username} - {self.created_at}"


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
