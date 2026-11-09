import hashlib
import uuid

from django.core.files.base import ContentFile
from django.db.models import F

from .models import DownloadEvent, Material, MaterialFile

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".zip", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 20 * 1024 * 1024          # 20 МБ на файл
MAX_MATERIAL_TOTAL = 100 * 1024 * 1024    # 100 МБ суммарно на материал


def store_material_files(material: Material, uploaded_files) -> list[str]:
    """Валидирует и сохраняет файлы материала. Возвращает список ошибок (пустой = успех)."""
    errors: list[str] = []

    if not uploaded_files:
        return ["Не приложено ни одного файла."]

    total_size = 0
    prepared = []  # (data: bytes, original_name: str, ext: str, mime: str, size: int)

    for uf in uploaded_files:
        name = (uf.name or "").strip()
        ext = ""
        if "." in name:
            ext = "." + name.rsplit(".", 1)[-1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"Файл «{name}»: недопустимый формат. Разрешены PDF, DOCX, ZIP, PNG, JPG.")
            continue

        data = uf.read()
        uf.seek(0)
        size = len(data)

        if size > MAX_FILE_SIZE:
            errors.append(f"Файл «{name}»: превышает 20 МБ.")
            continue

        total_size += size
        prepared.append((data, name, ext, uf.content_type or "", size))

    if total_size > MAX_MATERIAL_TOTAL:
        errors.append("Суммарный размер файлов материала превышает 100 МБ.")
        return errors

    if errors:
        return errors

    for data, original_name, ext, mime, size in prepared:
        uuid_name = f"{uuid.uuid4().hex}{ext}"
        checksum = hashlib.sha256(data).hexdigest()
        mf = MaterialFile(
            material=material,
            original_name=original_name,
            mime_type=mime,
            size_bytes=size,
            checksum_sha256=checksum,
        )
        mf.file.save(uuid_name, ContentFile(data), save=True)

    return []


def record_download(material: Material, file: MaterialFile, user) -> DownloadEvent:
    """Фиксирует скачивание и атомарно увеличивает счётчик."""
    event = DownloadEvent.objects.create(material=material, file=file, user=user)
    Material.objects.filter(pk=material.pk).update(download_count=F("download_count") + 1)
    material.refresh_from_db(fields=["download_count"])
    return event