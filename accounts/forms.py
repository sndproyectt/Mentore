from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import TeacherProfile, ROLE_CHOICES


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True,  label='Nombre')
    last_name  = forms.CharField(max_length=50, required=True,  label='Apellido')
    email      = forms.EmailField(required=True,                label='Correo electrónico')
    subject    = forms.CharField(max_length=120, required=False, label='Materia que enseña')

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'username', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email      = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name  = self.cleaned_data['last_name']
        if commit:
            user.save()
            TeacherProfile.objects.create(
                user=user,
                subject=self.cleaned_data.get('subject', ''),
                role='teacher',
            )
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Usuario',    widget=forms.TextInput())
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput())


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=False, label='Nombre')
    last_name  = forms.CharField(max_length=50, required=False, label='Apellido')
    email      = forms.EmailField(required=False,               label='Correo electrónico')

    class Meta:
        model  = TeacherProfile
        fields = [
            'bio', 'subject', 'phone', 'school_name', 'city', 'avatar',
            'is_homeroom_teacher', 'homeroom_group', 'theme_color',
        ]
        labels = {
            'bio':                 'Biografía',
            'subject':             'Materia principal',
            'phone':               'Teléfono',
            'school_name':         'Nombre del colegio',
            'city':                'Ciudad',
            'avatar':              'Foto de perfil',
            'is_homeroom_teacher': '¿Eres director(a) de grupo?',
            'homeroom_group':      'Grupo a tu cargo',
            'theme_color':         'Tema de color',
        }


# ── Formulario para que el coordinador gestione usuarios ──────
class TeacherRoleForm(forms.ModelForm):
    """Permite al coordinador cambiar el rol de un usuario."""
    class Meta:
        model  = TeacherProfile
        fields = ['role']
        labels = {'role': 'Rol'}
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
        }


class CoordinatorCreateTeacherForm(UserCreationForm):
    """Formulario que usa el coordinador para crear nuevos profesores."""
    first_name = forms.CharField(max_length=50, required=True,  label='Nombre')
    last_name  = forms.CharField(max_length=50, required=True,  label='Apellido')
    email      = forms.EmailField(required=True,                label='Correo electrónico')
    subject    = forms.CharField(max_length=120, required=False, label='Materia')
    role       = forms.ChoiceField(choices=ROLE_CHOICES,         label='Rol')

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'username', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email      = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name  = self.cleaned_data['last_name']
        if commit:
            user.save()
            TeacherProfile.objects.create(
                user=user,
                subject=self.cleaned_data.get('subject', ''),
                role=self.cleaned_data.get('role', 'teacher'),
            )
        return user
