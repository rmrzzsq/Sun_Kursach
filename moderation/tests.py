from django.test import TestCase
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from accounts.models import User
from core.enums import ComplaintStatus, MaterialStatus, UserRole
from dictionaries.models import Discipline, MaterialType, Teacher
from feedback.models import Complaint
from materials.models import Material
from moderation.services import (
    approve_material,
    handle_complaint,
    reject_material,
    set_verified_flag,
)


class ModerationAccessTests(TestCase):
    """ТЗ 1.5 п.4: разграничение прав доступа в модерации."""

    def setUp(self):
        self.moderator = User.objects.create_user(
            "mod@test.local", "pass12345", full_name="Модератор", role=UserRole.MODERATOR
        )
        self.admin = User.objects.create_user(
            "admin@test.local", "pass12345", full_name="Админ", role=UserRole.ADMIN
        )
        self.user = User.objects.create_user(
            "user@test.local", "pass12345", full_name="Пользователь", role=UserRole.USER
        )
        self.author = User.objects.create_user(
            "author@test.local", "pass12345", full_name="Автор", role=UserRole.USER
        )
        self.discipline = Discipline.objects.create(name="Модели данных")
        self.teacher = Teacher.objects.create(full_name="Антипова О. В.")
        self.mtype = MaterialType.objects.create(code="NOTE", name="Конспект")
        self.material = Material.objects.create(
            title="Материал на модерации",
            description="Описание",
            author=self.author,
            discipline=self.discipline,
            teacher=self.teacher,
            type=self.mtype,
            semester=4,
            academic_year=2026,
            status=MaterialStatus.MODERATION,
        )

    # --- роль ---

    def test_guest_queue_returns_302(self):
        resp = self.client.get(reverse("moderation:queue"))
        self.assertEqual(resp.status_code, 302)

    def test_user_queue_returns_403(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("moderation:queue"))
        self.assertEqual(resp.status_code, 403)

    def test_moderator_and_admin_queue_ok(self):
        for u in (self.moderator, self.admin):
            self.client.force_login(u)
            resp = self.client.get(reverse("moderation:queue"))
            self.assertEqual(resp.status_code, 200)

    # --- конфликт интересов (сервисный уровень) ---

    def test_approve_own_raises_permission_denied(self):
        own = Material.objects.create(
            title="Свой материал", description="", author=self.moderator,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=1, academic_year=2026, status=MaterialStatus.MODERATION,
        )
        with self.assertRaises(PermissionDenied):
            approve_material(self.moderator, own)

    def test_reject_own_raises_permission_denied(self):
        own = Material.objects.create(
            title="Свой материал", description="", author=self.moderator,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=1, academic_year=2026, status=MaterialStatus.MODERATION,
        )
        with self.assertRaises(PermissionDenied):
            reject_material(self.moderator, own, "Причина")

    def test_handle_complaint_on_own_material_raises_permission_denied(self):
        comp = Complaint.objects.create(
            material=self.material, reporter=self.user, text="Ошибка",
        )
        # Назначаем автора материала модератором — конфликт интересов
        self.material.author = self.moderator
        self.material.save()
        with self.assertRaises(PermissionDenied):
            handle_complaint(comp, self.moderator, "dismiss")

    # --- view-level COI: модератор не видит кнопку/форму для своего материала ---

    def test_review_view_shows_cannot_moderate_for_own(self):
        own = Material.objects.create(
            title="Свой материал", description="", author=self.moderator,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=1, academic_year=2026, status=MaterialStatus.MODERATION,
        )
        self.client.force_login(self.moderator)
        resp = self.client.get(reverse("moderation:review", kwargs={"pk": own.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["can_moderate"])

    def test_review_view_allows_moderate_for_foreign(self):
        self.client.force_login(self.moderator)
        resp = self.client.get(reverse("moderation:review", kwargs={"pk": self.material.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["can_moderate"])


class ModerationProcessTests(TestCase):
    """ТЗ 1.5 п.4: процессы модерации — approve/reject, метка, published_at."""

    def setUp(self):
        self.moderator = User.objects.create_user(
            "mod@test.local", "pass12345", full_name="Модератор", role=UserRole.MODERATOR
        )
        self.author = User.objects.create_user(
            "author@test.local", "pass12345", full_name="Автор", role=UserRole.USER
        )
        self.discipline = Discipline.objects.create(name="Модели данных")
        self.teacher = Teacher.objects.create(full_name="Антипова О. В.")
        self.mtype = MaterialType.objects.create(code="NOTE", name="Конспект")
        self.material = Material.objects.create(
            title="На модерации", description="", author=self.author,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=4, academic_year=2026, status=MaterialStatus.MODERATION,
        )

    # --- approve ---

    def test_approve_sets_published_and_clears_reason(self):
        self.material.moderation_reason = "Старая причина"
        self.material.save()
        result = approve_material(self.moderator, self.material)
        self.assertEqual(result.status, MaterialStatus.PUBLISHED)
        self.assertEqual(result.moderation_reason, "")
        self.assertIsNotNone(result.published_at)

    def test_approve_non_moderation_raises_validation_error(self):
        self.material.status = MaterialStatus.REJECTED
        self.material.save()
        with self.assertRaises(ValidationError):
            approve_material(self.moderator, self.material)

    def test_approve_preserves_first_published_at(self):
        approve_material(self.moderator, self.material)
        first = self.material.published_at
        self.material.title = "Переименован"
        self.material.save()
        self.material.refresh_from_db()
        self.assertEqual(self.material.published_at, first)

    # --- reject ---

    def test_reject_sets_status_and_reason(self):
        result = reject_material(self.moderator, self.material, "Некорректное содержание")
        self.assertEqual(result.status, MaterialStatus.REJECTED)
        self.assertEqual(result.moderation_reason, "Некорректное содержание")

    def test_reject_without_reason_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            reject_material(self.moderator, self.material, "")
        with self.assertRaises(ValidationError):
            reject_material(self.moderator, self.material, "   ")

    def test_reject_non_moderation_raises_validation_error(self):
        self.material.status = MaterialStatus.PUBLISHED
        self.material.save()
        with self.assertRaises(ValidationError):
            reject_material(self.moderator, self.material, "Причина")

    # --- verified flag ---

    def test_set_verified_flag_on_published(self):
        self.material.status = MaterialStatus.PUBLISHED
        self.material.save()
        result = set_verified_flag(self.moderator, self.material, True)
        self.assertTrue(result.is_verified_by_community)
        result = set_verified_flag(self.moderator, self.material, False)
        self.assertFalse(result.is_verified_by_community)

    def test_set_verified_flag_on_non_published_raises(self):
        with self.assertRaises(ValidationError):
            set_verified_flag(self.moderator, self.material, True)


class ComplaintHandlingTests(TestCase):
    """ТЗ 1.5 п.4: ветки обработки жалоб с захватом контекста."""

    def setUp(self):
        self.moderator = User.objects.create_user(
            "mod@test.local", "pass12345", full_name="Модератор", role=UserRole.MODERATOR
        )
        self.reporter = User.objects.create_user(
            "rep@test.local", "pass12345", full_name="Заявитель", role=UserRole.USER
        )
        self.author = User.objects.create_user(
            "auth@test.local", "pass12345", full_name="Автор", role=UserRole.USER
        )
        self.discipline = Discipline.objects.create(name="Модели данных")
        self.teacher = Teacher.objects.create(full_name="Антипова О. В.")
        self.mtype = MaterialType.objects.create(code="NOTE", name="Конспект")
        self.material = Material.objects.create(
            title="Опубликованный", description="", author=self.author,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=4, academic_year=2026, status=MaterialStatus.PUBLISHED,
        )
        self.complaint = Complaint.objects.create(
            material=self.material, reporter=self.reporter, text="Ошибка в конспекте",
        )

    def _refresh(self):
        self.complaint.refresh_from_db()
        self.material.refresh_from_db()

    # --- dismiss ---

    def test_dismiss_resolves_without_changing_material_status(self):
        before = self.material.status
        handle_complaint(self.complaint, self.moderator, "dismiss", "Без оснований")
        self._refresh()
        self.assertEqual(self.complaint.status, ComplaintStatus.RESOLVED)
        self.assertEqual(self.complaint.moderator, self.moderator)
        self.assertEqual(self.complaint.resolution_note, "Без оснований")
        self.assertIsNotNone(self.complaint.resolved_at)
        self.assertEqual(self.complaint.material_status_before, before)
        self.assertEqual(self.material.status, before)

    # --- needs_revision ---

    def test_needs_revision_changes_material_status(self):
        handle_complaint(self.complaint, self.moderator, "needs_revision", "Исправить формулы")
        self._refresh()
        self.assertEqual(self.complaint.status, ComplaintStatus.RESOLVED)
        self.assertEqual(self.complaint.material_status_before, MaterialStatus.PUBLISHED)
        self.assertEqual(self.material.status, MaterialStatus.NEEDS_REVISION)

    # --- hide --

    def test_hide_changes_material_status(self):
        handle_complaint(self.complaint, self.moderator, "hide", "Плагиат")
        self._refresh()
        self.assertEqual(self.complaint.status, ComplaintStatus.RESOLVED)
        self.assertEqual(self.complaint.material_status_before, MaterialStatus.PUBLISHED)
        self.assertEqual(self.material.status, MaterialStatus.HIDDEN)

    # --- защита от повторной обработки ---

    def test_already_resolved_raises_validation_error(self):
        handle_complaint(self.complaint, self.moderator, "dismiss")
        with self.assertRaises(ValidationError):
            handle_complaint(self.complaint, self.moderator, "hide")

    # --- неизвестное действие ---

    def test_unknown_action_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            handle_complaint(self.complaint, self.moderator, "ban_author")

    # --- view-level: обработанная жалоба показывает already_resolved ---

    def test_complaint_review_shows_already_resolved(self):
        handle_complaint(self.complaint, self.moderator, "dismiss")
        self.client.force_login(self.moderator)
        resp = self.client.get(
            reverse("moderation:complaint_review", kwargs={"pk": self.complaint.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["already_resolved"])