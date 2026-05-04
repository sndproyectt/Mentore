from django.db import models
from django.contrib.auth.models import User


class SocialAccount(models.Model):
    """Stores social login provider info linked to a Django user."""
    PROVIDER_CHOICES = [('google', 'Google'), ('apple', 'Apple')]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider    = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_id = models.CharField(max_length=255)
    email       = models.EmailField(blank=True)
    avatar_url  = models.URLField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('provider', 'provider_id')

    def __str__(self):
        return f"{self.provider} - {self.user.username}"

from django.db import models
from django.contrib.auth.models import User


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    bio = models.TextField(blank=True, null=True)
    subject = models.CharField(max_length=120, blank=True, verbose_name='Materia principal')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Teléfono')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Foto de perfil')
    school_name = models.CharField(max_length=150, blank=True, verbose_name='Nombre del colegio')
    city = models.CharField(max_length=100, blank=True, verbose_name='Ciudad')
    # Director de grupo
    is_homeroom_teacher = models.BooleanField(default=False, verbose_name='¿Es director(a) de grupo?')
    homeroom_group = models.CharField(max_length=100, blank=True, verbose_name='Grupo a cargo (dirección)')
    # Tema de color (estilo Google Classroom)
    theme_color = models.CharField(max_length=30, blank=True, default='ocean', verbose_name='Tema de color')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Perfil de {self.user.get_full_name() or self.user.username}"
