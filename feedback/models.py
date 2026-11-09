from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.enums import ComplaintStatus, MaterialStatus
from core.models import TimeStampedModel


class Review(TimeStampedModel):
    material = models.ForeignKey(
        "materials.Material",
        verbose_name="Материал",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    score = models.PositiveSmallIntegerField(
        "Оценка",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    text = models.TextField("Текст отзыва", blank=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["material", "user"],
                name="unique_review_per_user_per_material",
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.material}: {self.score}"


class Comment(models.Model):
    material = models.ForeignKey(
        "materials.Material",
        verbose_name="Материал",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    body = models.TextField("Текст комментария")
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} @ {self.material}"


class Complaint(models.Model):
    material = models.ForeignKey(
        "materials.Material",
        verbose_name="Материал",
        on_delete=models.CASCADE,
        related_name="complaints",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Заявитель",
        on_delete=models.CASCADE,
        related_name="complaints_filed",
    )
    text = models.TextField("Описание проблемы")
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=ComplaintStatus.choices,
        default=ComplaintStatus.NEW,
        db_index=True,
    )
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Модератор",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints_handled",
    )
    resolution_note = models.TextField("Решение модератора", blank=True)
    material_status_before = models.CharField(
        "Статус материала до обработки",
        max_length=20,
        choices=MaterialStatus.choices,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    resolved_at = models.DateTimeField("Дата обработки", null=True, blank=True)

    class Meta:
        verbose_name = "Жалоба"
        verbose_name_plural = "Жалобы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Жалоба на {self.material} от {self.reporter}"