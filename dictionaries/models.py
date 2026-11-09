from django.db import models

from core.models import TimeStampedModel


class Institution(TimeStampedModel):
    name = models.CharField("Название", max_length=255, unique=True)
    is_active = models.BooleanField("Активно", default=True)

    class Meta:
        verbose_name = "Учебное заведение"
        verbose_name_plural = "Учебные заведения"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Faculty(TimeStampedModel):
    institution = models.ForeignKey(
        Institution,
        verbose_name="Учебное заведение",
        on_delete=models.PROTECT,
        related_name="faculties",
    )
    name = models.CharField("Название", max_length=255)
    is_active = models.BooleanField("Активно", default=True)

    class Meta:
        verbose_name = "Факультет"
        verbose_name_plural = "Факультеты"
        ordering = ["institution__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="unique_faculty_per_institution",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.institution.name})"


class Department(TimeStampedModel):
    faculty = models.ForeignKey(
        Faculty,
        verbose_name="Факультет",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="departments",
    )
    name = models.CharField("Название", max_length=255)
    short_name = models.CharField("Краткое название", max_length=64, blank=True)
    is_active = models.BooleanField("Активно", default=True)

    class Meta:
        verbose_name = "Кафедра"
        verbose_name_plural = "Кафедры"
        ordering = ["faculty__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.short_name})" if self.short_name else self.name


class Discipline(TimeStampedModel):
    department = models.ForeignKey(
        Department,
        verbose_name="Кафедра",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disciplines",
    )
    code = models.CharField("Код дисциплины", max_length=64, blank=True)
    name = models.CharField("Название", max_length=255)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Дисциплина"
        verbose_name_plural = "Дисциплины"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} — {self.name}" if self.code else self.name


class Teacher(TimeStampedModel):
    institution = models.ForeignKey(
        Institution,
        verbose_name="Учебное заведение",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teachers",
    )
    faculty = models.ForeignKey(
        Faculty,
        verbose_name="Факультет",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teachers",
    )
    department = models.ForeignKey(
        Department,
        verbose_name="Кафедра",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teachers",
    )
    full_name = models.CharField("ФИО", max_length=255)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Преподаватель"
        verbose_name_plural = "Преподаватели"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class MaterialType(TimeStampedModel):
    code = models.CharField(
        "Код",
        max_length=50,
        unique=True,
        help_text="Например: NOTE, SOLUTION, METHOD, CHEAT_SHEET, EXAM_QUESTIONS",
    )
    name = models.CharField("Название", max_length=100)
    description = models.TextField("Описание", blank=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Тип материала"
        verbose_name_plural = "Типы материалов"
        ordering = ["name"]

    def __str__(self):
        return self.name