from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.enums import MaterialStatus, UserRole
from dictionaries.models import Discipline, MaterialType, Teacher
from materials.models import Material


class ReportsAccessTests(TestCase):
    """ТЗ 1.5 п.4: разграничение прав доступа к отчётам."""

    def setUp(self):
        self.admin = User.objects.create_user(
            "admin@test.local", "pass12345", full_name="Админ", role=UserRole.ADMIN
        )
        self.moderator = User.objects.create_user(
            "mod@test.local", "pass12345", full_name="Модератор", role=UserRole.MODERATOR
        )
        self.user = User.objects.create_user(
            "user@test.local", "pass12345", full_name="Пользователь", role=UserRole.USER
        )

    # --- гость ---

    def test_guest_activity_redirects_to_login(self):
        resp = self.client.get(reverse("reports:activity"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_guest_content_redirects_to_login(self):
        resp = self.client.get(reverse("reports:content"))
        self.assertEqual(resp.status_code, 302)

    def test_guest_log_redirects_to_login(self):
        resp = self.client.get(reverse("reports:log"))
        self.assertEqual(resp.status_code, 302)

    # --- пользователь и модератор ---

    def test_user_activity_returns_403(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("reports:activity"))
        self.assertEqual(resp.status_code, 403)

    def test_moderator_activity_returns_403(self):
        self.client.force_login(self.moderator)
        resp = self.client.get(reverse("reports:activity"))
        self.assertEqual(resp.status_code, 403)

    def test_user_content_returns_403(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("reports:content"))
        self.assertEqual(resp.status_code, 403)

    def test_admin_all_reports_ok(self):
        self.client.force_login(self.admin)
        for name in ("activity", "content", "log"):
            resp = self.client.get(reverse(f"reports:{name}"))
            self.assertEqual(resp.status_code, 200, msg=f"Отчёт {name} недоступен админу")


class ReportsPeriodFilterTests(TestCase):
    """Корректность фильтрации по периоду и метрики published_in_period."""

    def setUp(self):
        self.admin = User.objects.create_user(
            "admin@test.local", "pass12345", full_name="Админ", role=UserRole.ADMIN
        )
        self.discipline = Discipline.objects.create(name="Модели данных")
        self.teacher = Teacher.objects.create(full_name="Антипова О. В.")
        self.mtype = MaterialType.objects.create(code="NOTE", name="Конспект")

        # Материал, опубликованный давно
        old_mat = Material.objects.create(
            title="Старый", description="", author=self.admin,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=1, academic_year=2025, status=MaterialStatus.PUBLISHED,
        )
        # Принудительно ставим старую дату публикации (save() ставит now())
        from django.utils import timezone
        old_date = timezone.now() - timedelta(days=90)
        old_mat.published_at = old_date
        old_mat.save(update_fields=["published_at"])

        # Материал, опубликованный вчера
        recent_mat = Material.objects.create(
            title="Новый", description="", author=self.admin,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=1, academic_year=2026, status=MaterialStatus.PUBLISHED,
        )
        yesterday = timezone.now() - timedelta(days=1)
        recent_mat.published_at = yesterday
        recent_mat.save(update_fields=["published_at"])

        # Материал на модерации (не должен считаться в published_in_period)
        mod_mat = Material.objects.create(
            title="На модерации", description="", author=self.admin,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=1, academic_year=2026, status=MaterialStatus.MODERATION,
        )

    def test_no_filter_shows_all(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("reports:content"))
        self.assertEqual(resp.context["materials_total"], 3)
        self.assertEqual(resp.context["published_in_period"], 2)

    def test_recent_period_filters_published_correctly(self):
        """Период «вчера» должен показать 1 публикацию, а не 2."""
        self.client.force_login(self.admin)
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        resp = self.client.get(
            reverse("reports:content"),
            {"date_from": yesterday.isoformat(), "date_to": today.isoformat()},
        )
        self.assertEqual(resp.context["published_in_period"], 1)
        self.assertEqual(resp.context["materials_total"], 3)  # материалы не фильтруются по дате создания в этом тесте

    def test_empty_period_shows_zero_events(self):
        """Будущий период не должен показывать событий."""
        self.client.force_login(self.admin)
        future = date.today() + timedelta(days=30)
        resp = self.client.get(
            reverse("reports:activity"),
            {"date_from": future.isoformat(), "date_to": (future + timedelta(days=1)).isoformat()},
        )
        self.assertEqual(resp.context["registrations"], 0)
        self.assertEqual(resp.context["active_users"], 0)
        total = sum(resp.context["totals"].values())
        self.assertEqual(total, 0)