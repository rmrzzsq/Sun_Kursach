import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from core.enums import MaterialStatus, UserRole
from dictionaries.models import Discipline, MaterialType, Teacher
from materials.models import DownloadEvent, Material, MaterialFile

TEST_MEDIA = tempfile.mkdtemp(prefix="studyswap_test_media_")


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class MaterialAccessTests(TestCase):
    """ТЗ 1.5 п.4: разграничение прав доступа + поведение статусов/дат модели."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)

    def setUp(self):
        self.author = User.objects.create_user(
            "author@test.local", "pass12345", full_name="Автор Тестов", role=UserRole.USER
        )
        self.reader = User.objects.create_user(
            "reader@test.local", "pass12345", full_name="Читатель Тестов", role=UserRole.USER
        )
        self.discipline = Discipline.objects.create(name="Модели данных")
        self.teacher = Teacher.objects.create(full_name="Антипова О. В.")
        self.mtype = MaterialType.objects.create(code="NOTE", name="Конспект")
        self.published = self._material(MaterialStatus.PUBLISHED)
        self.file = self._file(self.published)

    def _material(self, status, author=None, title="Материал"):
        return Material.objects.create(
            title=title,
            description="Описание",
            author=author or self.author,
            discipline=self.discipline,
            teacher=self.teacher,
            type=self.mtype,
            semester=4,
            academic_year=2026,
            status=status,
        )

    def _file(self, material, name="test.pdf"):
        return MaterialFile.objects.create(
            material=material,
            file=SimpleUploadedFile(name, b"%PDF-1.4 test content", content_type="application/pdf"),
            original_name=name,
            size_bytes=21,
        )

    def _download_url(self, material=None, file=None):
        return reverse(
            "materials:file_download",
            kwargs={
                "material_pk": (material or self.published).pk,
                "file_pk": (file or self.file).pk,
            },
        )

    # --- скачивание: доступ ---

    def test_guest_download_redirects_and_creates_no_event(self):
        resp = self.client.get(self._download_url())
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(DownloadEvent.objects.count(), 0)

    def test_authenticated_download_creates_event_and_increments_counter(self):
        self.client.force_login(self.reader)
        resp = self.client.get(self._download_url())
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment", resp.get("Content-Disposition", ""))
        self.assertTrue(
            DownloadEvent.objects.filter(
                material=self.published, file=self.file, user=self.reader
            ).exists()
        )
        self.published.refresh_from_db()
        self.assertEqual(self.published.download_count, 1)
        self.client.get(self._download_url())
        self.published.refresh_from_db()
        self.assertEqual(self.published.download_count, 2)
        self.assertEqual(DownloadEvent.objects.count(), 2)

    def test_download_non_published_returns_404(self):
        self.client.force_login(self.reader)
        for status in (
            MaterialStatus.MODERATION,
            MaterialStatus.REJECTED,
            MaterialStatus.NEEDS_REVISION,
            MaterialStatus.HIDDEN,
            MaterialStatus.ARCHIVED,
        ):
            m = self._material(status, title=f"Материал {status}")
            f = self._file(m, name=f"{status}.pdf")
            resp = self.client.get(self._download_url(m, f))
            self.assertEqual(resp.status_code, 404, msg=f"статус {status} не должен скачиваться")
        self.assertEqual(DownloadEvent.objects.count(), 0)

    def test_download_foreign_file_via_published_material_returns_404(self):
        """IDOR-контроль: файл скрытого материала нельзя скачать через URL опубликованного."""
        hidden = self._material(MaterialStatus.HIDDEN, title="Скрытый")
        hidden_file = self._file(hidden, name="secret.pdf")
        self.client.force_login(self.reader)
        resp = self.client.get(self._download_url(self.published, hidden_file))
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(DownloadEvent.objects.count(), 0)

    # --- каталог и карточка: только PUBLISHED ---

    def test_catalog_lists_only_published(self):
        for status in (
            MaterialStatus.MODERATION,
            MaterialStatus.REJECTED,
            MaterialStatus.HIDDEN,
            MaterialStatus.ARCHIVED,
        ):
            self._material(status, title=f"Материал {status}")
        resp = self.client.get(reverse("materials:list"))
        self.assertEqual(resp.status_code, 200)
        pks = {m.pk for m in resp.context["object_list"]}
        self.assertEqual(pks, {self.published.pk})

    def test_detail_non_published_returns_404(self):
        for status in (
            MaterialStatus.MODERATION,
            MaterialStatus.REJECTED,
            MaterialStatus.NEEDS_REVISION,
            MaterialStatus.HIDDEN,
            MaterialStatus.ARCHIVED,
        ):
            m = self._material(status, title=f"Материал {status}")
            resp = self.client.get(reverse("materials:detail", kwargs={"pk": m.pk}))
            self.assertEqual(resp.status_code, 404, msg=f"статус {status} не должен открываться")

    def test_detail_published_ok_for_guest(self):
        resp = self.client.get(reverse("materials:detail", kwargs={"pk": self.published.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["can_download"])

    # --- поведение модели: даты статусов ---

    def test_save_sets_published_at_once_and_never_overwrites(self):
        m = self._material(MaterialStatus.MODERATION)
        self.assertIsNone(m.published_at)
        m.status = MaterialStatus.PUBLISHED
        m.save()
        first = m.published_at
        self.assertIsNotNone(first)
        m.title = "Переименован"
        m.save()
        m.refresh_from_db()
        self.assertEqual(m.published_at, first)

    def test_save_sets_archived_at_on_archive(self):
        m = self._material(MaterialStatus.PUBLISHED)
        self.assertIsNone(m.archived_at)
        m.status = MaterialStatus.ARCHIVED
        m.save()
        m.refresh_from_db()
        self.assertIsNotNone(m.archived_at)