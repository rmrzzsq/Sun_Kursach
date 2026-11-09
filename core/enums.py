from django.db import models


class UserRole(models.TextChoices):
    USER = "USER", "Пользователь"
    MODERATOR = "MODERATOR", "Модератор"
    ADMIN = "ADMIN", "Администратор"


class MaterialStatus(models.TextChoices):
    MODERATION = "MODERATION", "На модерации"
    PUBLISHED = "PUBLISHED", "Опубликован"
    REJECTED = "REJECTED", "Отклонён"
    NEEDS_REVISION = "NEEDS_REVISION", "На доработке"
    HIDDEN = "HIDDEN", "Скрыт"
    ARCHIVED = "ARCHIVED", "В архиве"


class ComplaintStatus(models.TextChoices):
    NEW = "NEW", "Новая"
    RESOLVED = "RESOLVED", "Обработана"