from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)

    list_display = (
        "email", "full_name", "role",
        "institution", "faculty", "course", "group",
        "is_active", "is_staff",
    )
    list_filter = ("role", "is_active", "is_staff", "institution", "faculty")
    search_fields = ("email", "full_name", "group")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личная информация", {"fields": ("full_name",)}),
        (
            "Данные StudySwap",
            {"fields": ("role", "institution", "faculty", "course", "group")},
        ),
        (
            "Права доступа",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email", "full_name", "role",
                    "institution", "faculty", "course", "group",
                    "password1", "password2",
                ),
            },
        ),
    )