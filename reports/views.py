from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views import View

from core.enums import UserRole

from .services import content_volume, parse_period, recent_log_entries, user_activity


class AdminRequiredMixin:
    """Доступ только администратору (ТЗ 1.4.2.4).

    LoginRequiredMixin стоит левее в MRO и отсекает гостей редиректом на вход;
    сюда доходят только аутентифицированные. getattr — второй рубеж на случай
    неверного порядка базовых классов.
    """

    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, "role", None) != UserRole.ADMIN:
            raise PermissionDenied("Отчёты доступны только администратору.")
        return super().dispatch(request, *args, **kwargs)


def _period_ctx(request):
    """Читает границы периода из GET, возвращает (dt_from, dt_to, контекст для формы)."""
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    dt_from, dt_to = parse_period(date_from, date_to)
    return dt_from, dt_to, {"date_from": date_from, "date_to": date_to}


class ActivityReportView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Сводная отчётность по активности пользователей."""

    def get(self, request):
        dt_from, dt_to, ctx = _period_ctx(request)
        ctx.update(user_activity(dt_from, dt_to))
        return render(request, "reports/activity.html", ctx)


class ContentVolumeView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Сводная отчётность по объёму загружаемого контента."""

    def get(self, request):
        dt_from, dt_to, ctx = _period_ctx(request)
        ctx.update(content_volume(dt_from, dt_to))
        return render(request, "reports/content.html", ctx)


class SystemLogView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Просмотр системного журнала действий (LogEntry Django)."""

    def get(self, request):
        return render(request, "reports/log.html", {"entries": recent_log_entries()})