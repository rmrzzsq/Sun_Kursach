from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models

from core.enums import UserRole


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Пользователь должен иметь email")

        email = self.normalize_email(email)

        extra_fields.setdefault("role", UserRole.USER)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("Email", unique=True)
    full_name = models.CharField("ФИО", max_length=255)
    role = models.CharField(
        "Роль",
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
    )

    institution = models.ForeignKey(
        "dictionaries.Institution",
        verbose_name="Учебное заведение",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    faculty = models.ForeignKey(
        "dictionaries.Faculty",
        verbose_name="Факультет",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    course = models.PositiveSmallIntegerField("Курс", null=True, blank=True)
    group = models.CharField("Группа", max_length=64, blank=True)

    is_active = models.BooleanField("Активен", default=True)
    is_staff = models.BooleanField("Доступ в админ-панель Django", default=False)
    date_joined = models.DateTimeField("Дата регистрации", auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["email"]

    def __str__(self):
        return f"{self.email} ({self.full_name})"

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.email

    @property
    def author_rating(self):
        from django.db.models import Avg
        from feedback.models import Review
        agg = Review.objects.filter(
            material__author=self,
            material__published_at__isnull=False,
        ).aggregate(Avg("score"))
        return agg["score__avg"]

    @property
    def has_moderation_access(self) -> bool:
        return self.role in (UserRole.MODERATOR, UserRole.ADMIN)
    
    @property
    def author_balance(self):
        from django.db.models import Count, Sum
        from feedback.models import Review
        agg = Review.objects.filter(
            material__author=self,
            material__published_at__isnull=False,
        ).aggregate(Sum("score"), Count("id"))
        total = agg["score__sum"] or 0
        count = agg["id__count"] or 0
        return total - 3 * count

