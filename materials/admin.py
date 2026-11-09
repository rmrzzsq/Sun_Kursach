from django.contrib import admin

from .models import Material, MaterialFile, Tag


class MaterialFileInline(admin.TabularInline):
    model = MaterialFile
    extra = 0
    readonly_fields = ("original_name", "mime_type", "size_bytes", "checksum_sha256", "uploaded_at")


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "title", "author", "discipline", "teacher", "type",
        "semester", "academic_year", "status",
        "is_verified_by_community", "average_rating", "download_count", "created_at",
    )
    list_filter = ("status", "type", "discipline", "teacher", "is_verified_by_community", "semester", "academic_year")
    search_fields = ("title", "description", "author__email", "author__full_name")
    autocomplete_fields = ("author", "discipline", "teacher", "type")
    filter_horizontal = ("tags",)
    readonly_fields = (
        "average_rating", "rating_count", "download_count",
        "published_at", "archived_at", "created_at", "updated_at",
    )
    inlines = [MaterialFileInline]

    fieldsets = (
        (None, {"fields": ("title", "description", "author")}),
        ("Атрибуты", {"fields": ("discipline", "teacher", "type", "tags", "semester", "academic_year")}),
        ("Модерация", {"fields": ("status", "is_verified_by_community", "moderation_reason")}),
        ("Метрики (только чтение)", {
            "fields": ("average_rating", "rating_count", "download_count", "published_at", "archived_at"),
            "classes": ("collapse",),
        }),
        ("Служебное", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)