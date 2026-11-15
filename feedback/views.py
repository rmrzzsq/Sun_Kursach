from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from core.enums import MaterialStatus
from materials.models import Material

from .forms import CommentForm, ReviewForm
from .models import Comment
from .services import create_or_update_review, submit_complaint


def _published_material(pk):
    return get_object_or_404(Material, pk=pk, status=MaterialStatus.PUBLISHED)


class ReviewCreateView(LoginRequiredMixin, View):
    """POST: поставить/обновить оценку. Допуск по скачиванию — в сервисе; запрет самооценки — здесь."""

    def post(self, request, material_pk):
        material = _published_material(material_pk)
        if material.author_id == request.user.pk:
            messages.error(request, "Нельзя оценивать собственный материал.")
            return redirect("materials:detail", pk=material_pk)
        form = ReviewForm(request.POST)
        if not form.is_valid():
            msg = form.errors["score"][0] if "score" in form.errors else "Проверьте данные оценки."
            messages.error(request, msg)
            return redirect("materials:detail", pk=material_pk)
        try:
            create_or_update_review(
                request.user, material, form.cleaned_data["score"], form.cleaned_data.get("text", "")
            )
        except ValidationError as e:
            messages.error(request, e.messages[0] if e.messages else str(e))
        else:
            messages.success(request, "Оценка сохранена.")
        return redirect("materials:detail", pk=material_pk)


class CommentCreateView(LoginRequiredMixin, View):
    """POST: добавить комментарий. Доступен любому авторизованному, включая автора."""

    def post(self, request, material_pk):
        material = _published_material(material_pk)
        form = CommentForm(request.POST)
        if not form.is_valid():
            msg = form.errors["body"][0] if "body" in form.errors else "Проверьте текст комментария."
            messages.error(request, msg)
            return redirect("materials:detail", pk=material_pk)
        Comment.objects.create(material=material, user=request.user, body=form.cleaned_data["body"])
        messages.success(request, "Комментарий добавлен.")
        return redirect("materials:detail", pk=material_pk)


class ComplaintSubmitView(LoginRequiredMixin, View):
    """POST: подать жалобу. Редирект жёстко на карточку (next убран — исключаем open redirect)."""

    def post(self, request, material_pk):
        material = _published_material(material_pk)
        text = request.POST.get("text", "")
        try:
            submit_complaint(request.user, material, text)
        except ValidationError as e:
            messages.error(request, e.messages[0] if e.messages else str(e))
        else:
            messages.success(request, "Жалоба отправлена модератору.")
        return redirect("materials:detail", pk=material_pk)