from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.encoding import escape_uri_path
from django.views import View

from core.enums import ComplaintStatus, MaterialStatus
from feedback.models import Complaint
from materials.models import Material, MaterialFile

from .services import approve_material, handle_complaint, reject_material, set_verified_flag


class ModeratorRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, "has_moderation_access", False):
            raise PermissionDenied("Раздел модерации доступен только модератору или администратору.")
        return super().dispatch(request, *args, **kwargs)


class ModerationQueueView(LoginRequiredMixin, ModeratorRequiredMixin, View):
    def get(self, request):
        materials = (
            Material.objects
            .filter(status=MaterialStatus.MODERATION)
            .select_related("author", "discipline", "teacher", "type")
            .order_by("created_at")
        )
        return render(request, "moderation/queue.html", {"materials": materials})


class ModerationReviewView(LoginRequiredMixin, ModeratorRequiredMixin, View):
    def _ctx(self, request, material):
        return {
            "material": material,
            "can_moderate": material.status == MaterialStatus.MODERATION,
            "can_verify": material.status == MaterialStatus.PUBLISHED,
            "is_own": material.author_id == request.user.pk,
        }

    def get(self, request, pk):
        material = get_object_or_404(
            Material.objects.select_related("author", "discipline", "teacher", "type"), pk=pk
        )
        return render(request, "moderation/review.html", self._ctx(request, material))

    def post(self, request, pk):
        material = get_object_or_404(Material, pk=pk)
        action = request.POST.get("action")
        try:
            if action == "approve":
                approve_material(request.user, material)
                messages.success(request, "Материал опубликован.")
                return redirect("moderation:queue")
            if action == "reject":
                reject_material(request.user, material, request.POST.get("reason", ""))
                messages.success(request, "Материал отклонён.")
                return redirect("moderation:queue")
            if action in ("verify", "unverify"):
                set_verified_flag(request.user, material, action == "verify")
                messages.success(request, "Метка обновлена.")
                return redirect("moderation:review", pk=pk)
        except ValidationError as e:
            messages.error(request, e.messages[0] if e.messages else str(e))
            return redirect("moderation:queue")
        raise Http404("Неизвестное действие.")


class ModerationFileDownloadView(LoginRequiredMixin, ModeratorRequiredMixin, View):
    def get(self, request, pk, file_pk):
        material = get_object_or_404(Material, pk=pk)
        file = get_object_or_404(MaterialFile, pk=file_pk, material=material)
        response = FileResponse(file.file.open("rb"), as_attachment=True, filename=file.original_name)
        response["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{escape_uri_path(file.original_name)}"
        )
        return response


class ComplaintQueueView(LoginRequiredMixin, ModeratorRequiredMixin, View):
    def get(self, request):
        complaints = (
            Complaint.objects
            .filter(status=ComplaintStatus.NEW)
            .select_related(
                "material", "material__author", "material__discipline",
                "material__teacher", "material__type", "reporter",
            )
            .order_by("created_at")
        )
        return render(request, "moderation/complaint_queue.html", {"complaints": complaints})


class ComplaintReviewView(LoginRequiredMixin, ModeratorRequiredMixin, View):
    def _ctx(self, request, complaint):
        material = complaint.material
        return {
            "complaint": complaint,
            "is_own": material.author_id == request.user.pk,
            "already_resolved": complaint.status != ComplaintStatus.NEW,
        }

    def get(self, request, pk):
        complaint = get_object_or_404(
            Complaint.objects.select_related(
                "material", "material__author", "material__discipline",
                "material__teacher", "material__type", "reporter",
            ),
            pk=pk,
        )
        return render(request, "moderation/complaint_review.html", self._ctx(request, complaint))

    def post(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        action = request.POST.get("action")
        note = request.POST.get("note", "")
        try:
            handle_complaint(complaint, request.user, action, note)
        except ValidationError as e:
            messages.error(request, e.messages[0] if e.messages else str(e))
            return redirect("moderation:complaint_review", pk=pk)
        # PermissionDenied (конфликт интересов / не модератор) не перехватываем -> 403.
        messages.success(request, "Жалоба обработана.")
        return redirect("moderation:complaint_queue")