from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import User
from core.enums import MaterialStatus, UserRole
from dictionaries.models import Discipline, MaterialType, Teacher
from feedback.models import Complaint, Review
from feedback.services import create_or_update_review, recalculate_material_metrics, submit_complaint
from materials.models import DownloadEvent, Material


class FeedbackAccessTests(TestCase):
    """ТЗ 1.5 п.4: доступ к оценке и подаче жалобы."""

    def setUp(self):
        self.author = User.objects.create_user(
            "author@test.local", "pass12345", full_name="Автор", role=UserRole.USER
        )
        self.reader = User.objects.create_user(
            "reader@test.local", "pass12345", full_name="Читатель", role=UserRole.USER
        )
        self.discipline = Discipline.objects.create(name="Модели данных")
        self.teacher = Teacher.objects.create(full_name="Антипова О. В.")
        self.mtype = MaterialType.objects.create(code="NOTE", name="Конспект")
        self.material = Material.objects.create(
            title="Опубликованный", description="", author=self.author,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=4, academic_year=2026, status=MaterialStatus.PUBLISHED,
        )

    # --- оценка: допуск по скачиванию ---

    def test_review_without_download_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            create_or_update_review(self.reader, self.material, 5)

    def test_review_with_download_succeeds(self):
        file = self.material.files.create(original_name="f.pdf", size_bytes=100)
        DownloadEvent.objects.create(material=self.material, file=file, user=self.reader)
        review, created = create_or_update_review(self.reader, self.material, 5, "Отлично")
        self.assertTrue(created)
        self.assertEqual(review.score, 5)
        self.assertEqual(review.text, "Отлично")

    def test_review_update_existing_does_not_create_new(self):
        file = self.material.files.create(original_name="f.pdf", size_bytes=100)
        DownloadEvent.objects.create(material=self.material, file=file, user=self.reader)
        r1, c1 = create_or_update_review(self.reader, self.material, 4)
        self.assertTrue(c1)
        r2, c2 = create_or_update_review(self.reader, self.material, 5, "Переоценка")
        self.assertFalse(c2)
        self.assertEqual(r2.pk, r1.pk)
        self.assertEqual(r2.score, 5)
        self.assertEqual(r2.text, "Переоценка")

    # --- оценка: неопубликованное ---

    def test_review_non_published_raises(self):
        self.material.status = MaterialStatus.MODERATION
        self.material.save()
        file = self.material.files.create(original_name="f.pdf", size_bytes=100)
        DownloadEvent.objects.create(material=self.material, file=file, user=self.reader)
        with self.assertRaises(ValidationError):
            create_or_update_review(self.reader, self.material, 5)

    # --- запрет самооценки (сервисный уровень; view-level проверяется в materials/tests через is_own) ---

    def test_author_can_review_own_material_service_allows_but_view_blocks(self):
        """Сервис технически разрешает (универсальность для админки/скриптов);
        запрет самооценки реализован в ReviewCreateView.post."""
        file = self.material.files.create(original_name="f.pdf", size_bytes=100)
        DownloadEvent.objects.create(material=self.material, file=file, user=self.author)
        review, created = create_or_update_review(self.author, self.material, 5)
        self.assertTrue(created)
        self.assertEqual(review.score, 5)

    # --- жалоба: допуск ---

    def test_complaint_on_non_published_raises(self):
        self.material.status = MaterialStatus.MODERATION
        self.material.save()
        with self.assertRaises(ValidationError):
            submit_complaint(self.reader, self.material, "Ошибка")

    def test_complaint_empty_text_raises(self):
        with self.assertRaises(ValidationError):
            submit_complaint(self.reader, self.material, "")
        with self.assertRaises(ValidationError):
            submit_complaint(self.reader, self.material, "   ")

    # --- жалоба: блок дубля ---

    def test_duplicate_active_complaint_raises(self):
        Complaint.objects.create(material=self.material, reporter=self.reader, text="Первая")
        with self.assertRaises(ValidationError):
            submit_complaint(self.reader, self.material, "Вторая")

    def test_resolved_complaint_does_not_block_new(self):
        comp = Complaint.objects.create(material=self.material, reporter=self.reader, text="Первая")
        comp.status = "RESOLVED"
        comp.save()
        new_comp = submit_complaint(self.reader, self.material, "Новая проблема")
        self.assertEqual(new_comp.status, "NEW")

    # --- разные пользователи могут жаловаться на один материал ---

    def test_different_users_can_complain_same_material(self):
        other = User.objects.create_user("other@test.local", "pass12345", role=UserRole.USER)
        Complaint.objects.create(material=self.material, reporter=self.reader, text="От reader")
        comp = submit_complaint(other, self.material, "От other")
        self.assertEqual(comp.reporter, other)


class MetricsRecalculationTests(TestCase):
    """ТЗ 1.5 п.4: пересчёт кэшированных метрик и рейтинга/баланса автора."""

    def setUp(self):
        self.author = User.objects.create_user(
            "author@test.local", "pass12345", full_name="Автор", role=UserRole.USER
        )
        self.discipline = Discipline.objects.create(name="Модели данных")
        self.teacher = Teacher.objects.create(full_name="Антипова О. В.")
        self.mtype = MaterialType.objects.create(code="NOTE", name="Конспект")
        self.material = Material.objects.create(
            title="Материал", description="", author=self.author,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=4, academic_year=2026, status=MaterialStatus.PUBLISHED,
        )

    def _reviewers(self, scores):
        """Создаёт N пользователей, ставит оценку score[i] и возвращает список пользователей."""
        users = []
        for i, s in enumerate(scores):
            u = User.objects.create_user(f"r{i}@test.local", "pass12345", role=UserRole.USER)
            f = self.material.files.create(original_name=f"f{i}.pdf", size_bytes=100)
            DownloadEvent.objects.create(material=self.material, file=f, user=u)
            create_or_update_review(u, self.material, s)
            users.append(u)
        return users

    def test_single_review_sets_avg_and_count(self):
        self._reviewers([4])
        self.material.refresh_from_db()
        self.assertEqual(self.material.average_rating, 4.00)
        self.assertEqual(self.material.rating_count, 1)

    def test_multiple_reviews_recalculates_avg(self):
        self._reviewers([3, 4, 5])
        self.material.refresh_from_db()
        self.assertAlmostEqual(float(self.material.average_rating), 4.00, places=2)
        self.assertEqual(self.material.rating_count, 3)

    def test_update_existing_review_updates_avg(self):
        users = self._reviewers([4])
        self.material.refresh_from_db()
        self.assertEqual(self.material.average_rating, 4.00)
        create_or_update_review(users[0], self.material, 5)
        self.material.refresh_from_db()
        self.assertEqual(self.material.average_rating, 5.00)
        self.assertEqual(self.material.rating_count, 1)

    def test_no_reviews_clears_avg(self):
        users = self._reviewers([4])
        Review.objects.filter(user=users[0]).delete()
        recalculate_material_metrics(self.material)
        self.material.refresh_from_db()
        self.assertIsNone(self.material.average_rating)
        self.assertEqual(self.material.rating_count, 0)

    # --- рейтинг и баланс автора ---

    def test_author_rating_is_avg_of_published_materials_only(self):
        """Рейтинг автора считается только по PUBLISHED-материалам.
        Оценки к MODERATION/REJECTED/HIDDEN/ARCHIVED не создаются (сервис блокирует),
        поэтому они автоматически не попадают в агрегат."""
        m1 = Material.objects.create(
            title="M1", description="", author=self.author,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=1, academic_year=2026, status=MaterialStatus.PUBLISHED,
        )
        # Второй материал остаётся в MODERATION — оценки к нему создать нельзя
        Material.objects.create(
            title="M2", description="", author=self.author,
            discipline=self.discipline, teacher=self.teacher, type=self.mtype,
            semester=2, academic_year=2026, status=MaterialStatus.MODERATION,
        )
        u = User.objects.create_user("r@test.local", "pass12345", role=UserRole.USER)
        f1 = m1.files.create(original_name="f1.pdf", size_bytes=100)
        DownloadEvent.objects.create(material=m1, file=f1, user=u)
        create_or_update_review(u, m1, 4)
        # Рейтинг = 4.00 (только один отзыв к опубликованному)
        self.assertAlmostEqual(float(self.author.author_rating), 4.00, places=2)

    def test_author_balance_formula(self):
        """balance = Σ(score) − 3 × N по опубликованным материалам."""
        self._reviewers([4, 5, 3])
        # Σ = 12, N = 3 → balance = 12 − 9 = 3
        self.assertEqual(self.author.author_balance, 3)

    def test_neutral_score_3_gives_zero_balance_contribution(self):
        self._reviewers([3, 3])
        self.assertEqual(self.author.author_balance, 0)

    def test_low_scores_give_negative_balance(self):
        self._reviewers([1, 2])
        # Σ = 3, N = 2 → balance = 3 − 6 = −3
        self.assertEqual(self.author.author_balance, -3)