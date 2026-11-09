from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from core.enums import MaterialStatus
from materials.models import Material

from .services import submit_complaint


class ComplaintSubmitView(LoginRequiredMixin, View):
    """POST-эндпоинт подачи жалобы. Форма встраивается в карточку материала (шаг 3.5)."""

    def post(self, request, material_pk):
        material = get_object_or_404(Material, pk=material_pk, status=MaterialStatus.PUBLISHED)
        text = request.POST.get("text", "")
        try:
            submit_complaint(request.user, material, text)
        except ValidationError as e:
            messages.error(request, e.messages[0] if e.messages else str(e))
        else:
            messages.success(request, "Жалоба отправлена модератору.")
        return redirect(request.POST.get("next") or "core:home")