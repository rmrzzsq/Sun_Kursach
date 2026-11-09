from django.core.exceptions import ValidationError
from django.db.models import Avg, Count

from core.enums import ComplaintStatus, MaterialStatus
from materials.models import DownloadEvent, Material

from .models import Complaint, Review


def recalculate_material_metrics(material: Material) -> None:
    agg = Review.objects.filter(material=material).aggregate(avg=Avg("score"), cnt=Count("id"))
    Material.objects.filter(pk=material.pk).update(average_rating=agg["avg"], rating_count=agg["cnt"] or 0)
    material.refresh_from_db(fields=["average_rating", "rating_count"])


def create_or_update_review(user, material: Material, score: int, text: str = ""):
    if material.status != MaterialStatus.PUBLISHED:
        raise ValidationError("Оценивать можно только опубликованные материалы.")
    if not DownloadEvent.objects.filter(material=material, user=user).exists():
        raise ValidationError("Оценка доступна только для скачанных материалов.")
    review, created = Review.objects.update_or_create(
        material=material, user=user, defaults={"score": score, "text": text}
    )
    recalculate_material_metrics(material)
    return review, created


def submit_complaint(user, material: Material, text: str) -> Complaint:
    if material.status != MaterialStatus.PUBLISHED:
        raise ValidationError("Жалобу можно подать только на опубликованный материал.")
    text = (text or "").strip()
    if not text:
        raise ValidationError("Опишите проблему в жалобе.")
    if Complaint.objects.filter(material=material, reporter=user, status=ComplaintStatus.NEW).exists():
        raise ValidationError("У вас уже есть необработанная жалоба на этот материал.")
    return Complaint.objects.create(material=material, reporter=user, text=text, status=ComplaintStatus.NEW)