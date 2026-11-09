from django.conf import settings
from django.db import models

from core.enums import MaterialStatus
from core.models import TimeStampedModel

from django.utils import timezone

class Tag(models.Model):
    name = models.CharField("Название тега", max_length=100, unique=True)

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Material(TimeStampedModel):
    title = models.CharField("Название материала", max_length=255)
    description = models.TextField("Описание")

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Автор",
        on_delete=models.PROTECT,
        related_name="materials",
    )
    discipline = models.ForeignKey(
        "dictionaries.Discipline",
        verbose_name="Дисциплина",
        on_delete=models.PROTECT,
        related_name="materials",
    )
    teacher = models.ForeignKey(
        "dictionaries.Teacher",
        verbose_name="Преподаватель",
        on_delete=models.PROTECT,
        related_name="materials",
    )
    type = models.ForeignKey(
        "dictionaries.MaterialType",
        verbose_name="Тип материала",
        on_delete=models.PROTECT,
        related_name="materials",
    )
    tags = models.ManyToManyField(Tag, verbose_name="Теги", blank=True, related_name="materials")

    semester = models.PositiveSmallIntegerField("Семестр")
    academic_year = models.PositiveIntegerField(
        "Учебный год", help_text="Стартовый год, напр. 2026 для 2026/2027"
    )

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=MaterialStatus.choices,
        default=MaterialStatus.MODERATION,
        db_index=True,
    )
    is_verified_by_community = models.BooleanField("Проверено сообществом", default=False)
    moderation_reason = models.TextField("Причина модерации", blank=True)

    average_rating = models.DecimalField(
        "Средний рейтинг", max_digits=3, decimal_places=2, null=True, blank=True, editable=False
    )
    rating_count = models.PositiveIntegerField("Количество оценок", default=0, editable=False)
    download_count = models.PositiveIntegerField("Количество скачиваний", default=0, editable=False)

    published_at = models.DateTimeField("Опубликован", null=True, blank=True, editable=False)
    archived_at = models.DateTimeField("В архиве", null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "Учебный материал"
        verbose_name_plural = "Учебные материалы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["author"]),
            models.Index(fields=["discipline"]),
            models.Index(fields=["teacher"]),
            models.Index(fields=["type"]),
            models.Index(fields=["semester", "academic_year"]),
        ]

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.status == MaterialStatus.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        if self.status == MaterialStatus.ARCHIVED and self.archived_at is None:
            self.archived_at = timezone.now()
        super().save(*args, **kwargs)

class MaterialFile(models.Model):
    material = models.ForeignKey(
        Material,
        verbose_name="Материал",
        on_delete=models.CASCADE,
        related_name="files",
    )

    file = models.FileField("Файл", upload_to="materials/files/%Y/%m/")
    original_name = models.CharField("Исходное имя", max_length=255)
    mime_type = models.CharField("MIME-тип", max_length=100, blank=True)
    size_bytes = models.BigIntegerField("Размер, байт", default=0)
    checksum_sha256 = models.CharField("SHA-256", max_length=64, blank=True)
    uploaded_at = models.DateTimeField("Загружен", auto_now_add=True)

    class Meta:
        verbose_name = "Файл материала"
        verbose_name_plural = "Файлы материалов"
        ordering = ["uploaded_at"]

    def __str__(self):
        return self.original_name

class DownloadEvent(models.Model):
    material = models.ForeignKey(
        Material,
        verbose_name="Материал",
        on_delete=models.CASCADE,
        related_name="download_events",
    )
    file = models.ForeignKey(
        MaterialFile,
        verbose_name="Файл",
        on_delete=models.CASCADE,
        related_name="download_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="download_events",
    )
    downloaded_at = models.DateTimeField("Дата скачивания", auto_now_add=True)

    class Meta:
        verbose_name = "Событие скачивания"
        verbose_name_plural = "События скачиваний"
        ordering = ["-downloaded_at"]
        indexes = [
            models.Index(fields=["material", "user"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.material} @ {self.downloaded_at:%Y-%m-%d %H:%M}"