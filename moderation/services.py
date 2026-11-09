from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from core.enums import ComplaintStatus, MaterialStatus, UserRole
from feedback.models import Complaint
from materials.models import Material


def _assert_moderator(user):
    if not user.is_authenticated or user.role not in (UserRole.MODERATOR, UserRole.ADMIN):
        raise PermissionDenied("Модерация доступна только модератору или администратору.")


def _assert_not_own(user, material: Material):
    if material.author_id == user.pk:
        raise PermissionDenied("Нельзя модерировать собственный материал.")


def approve_material(moderator, material):
    _assert_moderator(moderator)
    _assert_not_own(moderator, material)
    if material.status != MaterialStatus.MODERATION:
        raise ValidationError("Утверждать можно только материалы со статусом «На модерации».")
    material.status = MaterialStatus.PUBLISHED
    material.moderation_reason = ""
    material.save()
    return material


def reject_material(moderator, material, reason):
    _assert_moderator(moderator)
    _assert_not_own(moderator, material)
    if material.status != MaterialStatus.MODERATION:
        raise ValidationError("Отклонять можно только материалы со статусом «На модерации».")
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("Укажите причину отклонения.")
    material.status = MaterialStatus.REJECTED
    material.moderation_reason = reason
    material.save()
    return material


def set_verified_flag(moderator, material, value):
    _assert_moderator(moderator)
    _assert_not_own(moderator, material)
    if material.status != MaterialStatus.PUBLISHED:
        raise ValidationError("Метку «Проверено сообществом» можно ставить только опубликованным материалам.")
    material.is_verified_by_community = bool(value)
    material.save()
    return material


COMPLAINT_ACTIONS = {"dismiss", "needs_revision", "hide"}


def handle_complaint(complaint: Complaint, moderator, action: str, note: str = "") -> Complaint:
    _assert_moderator(moderator)
    _assert_not_own(moderator, complaint.material)
    if complaint.status != ComplaintStatus.NEW:
        raise ValidationError("Эта жалоба уже обработана.")
    if action not in COMPLAINT_ACTIONS:
        raise ValidationError("Неизвестное действие по жалобе.")

    material = complaint.material
    complaint.material_status_before = material.status

    if action == "needs_revision":
        material.status = MaterialStatus.NEEDS_REVISION
        material.save()
    elif action == "hide":
        material.status = MaterialStatus.HIDDEN
        material.save()
    # dismiss: статус материала не меняется

    complaint.status = ComplaintStatus.RESOLVED
    complaint.moderator = moderator
    complaint.resolution_note = (note or "").strip()
    complaint.resolved_at = timezone.now()
    complaint.save()
    return complaint