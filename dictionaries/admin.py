from django.contrib import admin

from .models import (
    Department, Discipline, Faculty,
    Institution, MaterialType, Teacher,
)


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at", "updated_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "is_active", "created_at")
    search_fields = ("name", "institution__name")
    list_filter = ("is_active", "institution")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "faculty", "is_active", "created_at")
    search_fields = ("name", "short_name", "faculty__name")
    list_filter = ("is_active", "faculty")


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "department", "is_active", "created_at")
    search_fields = ("name", "code", "department__name")
    list_filter = ("is_active", "department")


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("full_name", "institution", "faculty", "department", "is_active")
    search_fields = ("full_name", "institution__name", "faculty__name", "department__name")
    list_filter = ("is_active", "institution", "faculty", "department")


@admin.register(MaterialType)
class MaterialTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    search_fields = ("name", "code")
    list_filter = ("is_active",)