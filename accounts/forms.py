from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)

from core.forms import BootstrapFormMixin
from dictionaries.models import Faculty, Institution

from .models import User


class SignUpForm(BootstrapFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = (
            "email",
            "full_name",
            "institution",
            "faculty",
            "course",
            "group",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["institution"].queryset = Institution.objects.filter(is_active=True)
        self.fields["faculty"].queryset = Faculty.objects.filter(is_active=True)
        self.fields["email"].label = "Email"
        self.fields["full_name"].label = "ФИО"
        self.fields["institution"].label = "Учебное заведение"
        self.fields["faculty"].label = "Факультет"
        self.fields["course"].label = "Курс"
        self.fields["group"].label = "Группа"
        self.fields["password1"].label = "Пароль"
        self.fields["password2"].label = "Подтверждение пароля"
        self.fields["password2"].help_text = "Введите тот же пароль, что и выше, для проверки."


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email"
        self.fields["username"].widget.attrs.update({"autofocus": True, "inputmode": "email"})


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("full_name", "email", "institution", "faculty", "course", "group")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["institution"].queryset = Institution.objects.filter(is_active=True)
        self.fields["faculty"].queryset = Faculty.objects.filter(is_active=True)
        self.fields["full_name"].label = "ФИО"
        self.fields["email"].label = "Email"
        self.fields["email"].help_text = "При смене используйте новый email для входа в систему."
        self.fields["institution"].label = "Учебное заведение"
        self.fields["faculty"].label = "Факультет"
        self.fields["course"].label = "Курс"
        self.fields["group"].label = "Группа"


class StudySwapPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Текущий пароль"
        self.fields["new_password1"].label = "Новый пароль"
        self.fields["new_password2"].label = "Подтверждение нового пароля"
        self.fields["new_password2"].help_text = "Введите тот же пароль, что и выше, для проверки."