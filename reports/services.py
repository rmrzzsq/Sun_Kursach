from datetime import datetime, time

from django.contrib.admin.models import LogEntry
from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.models import User
from core.enums import MaterialStatus
from feedback.models import Comment, Complaint, Review
from materials.models import DownloadEvent, Material, MaterialFile


def parse_period(date_from=None, date_to=None):
    """YYYY-MM-DD -> осведомлённые границы [00:00:00, 23:59:59.999999]. None -> открытая граница."""
    tz = timezone.get_current_timezone()
    dt_from = dt_to = None
    d = parse_date(date_from) if date_from else None
    if d:
        dt_from = timezone.make_aware(datetime.combine(d, time.min), tz)
    d = parse_date(date_to) if date_to else None
    if d:
        dt_to = timezone.make_aware(datetime.combine(d, time.max), tz)
    return dt_from, dt_to


def _in_period(qs, field, dt_from, dt_to):
    if dt_from is not None:
        qs = qs.filter(**{f"{field}__gte": dt_from})
    if dt_to is not None:
        qs = qs.filter(**{f"{field}__lte": dt_to})
    return qs


def _user_counts(model, user_field, date_field, dt_from, dt_to):
    qs = _in_period(model.objects.all(), date_field, dt_from, dt_to)
    return dict(qs.values_list(user_field).annotate(c=Count("id")))


def user_activity(dt_from=None, dt_to=None):
    """Отчёт по активности пользователей (ТЗ 1.4.2.4)."""
    uploads = _user_counts(Material, "author_id", "created_at", dt_from, dt_to)
    downloads = _user_counts(DownloadEvent, "user_id", "downloaded_at", dt_from, dt_to)
    reviews = _user_counts(Review, "user_id", "created_at", dt_from, dt_to)
    comments = _user_counts(Comment, "user_id", "created_at", dt_from, dt_to)
    complaints = _user_counts(Complaint, "reporter_id", "created_at", dt_from, dt_to)

    rows = []
    for u in User.objects.order_by("full_name", "email"):
        row = {
            "user_id": u.pk,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.get_role_display(),
            "uploads": uploads.get(u.pk, 0),
            "downloads": downloads.get(u.pk, 0),
            "reviews": reviews.get(u.pk, 0),
            "comments": comments.get(u.pk, 0),
            "complaints": complaints.get(u.pk, 0),
        }
        row["total"] = (
            row["uploads"] + row["downloads"] + row["reviews"] + row["comments"] + row["complaints"]
        )
        rows.append(row)

    keys = ("uploads", "downloads", "reviews", "comments", "complaints")
    totals = {k: sum(r[k] for r in rows) for k in keys}
    registrations = _in_period(User.objects.all(), "date_joined", dt_from, dt_to).count()
    active_users = sum(1 for r in rows if r["total"] > 0)
    return {
        "rows": rows,
        "totals": totals,
        "registrations": registrations,
        "active_users": active_users,
    }


def content_volume(dt_from=None, dt_to=None):
    """Отчёт по объёму загружаемого контента (ТЗ 1.4.2.4)."""
    mats = _in_period(Material.objects.all(), "created_at", dt_from, dt_to)
    files = _in_period(MaterialFile.objects.all(), "material__created_at", dt_from, dt_to)

    by_status = [
        {"code": s.value, "label": s.label, "count": mats.filter(status=s.value).count()}
        for s in MaterialStatus
    ]
    by_type = [
        {"name": r["type__name"], "count": r["count"]}
        for r in mats.values("type__name").annotate(count=Count("id")).order_by("-count")
    ]
    by_discipline = [
        {"name": r["discipline__name"], "count": r["count"], "downloads": r["downloads"] or 0}
        for r in mats.values("discipline__name")
        .annotate(count=Count("id"), downloads=Sum("download_count"))
        .order_by("-count")
    ]
    return {
        "materials_total": mats.count(),
        "by_status": by_status,
        "files_count": files.count(),
        "total_bytes": files.aggregate(s=Sum("size_bytes"))["s"] or 0,
        "published_in_period": _in_period(
        Material.objects.filter(published_at__isnull=False), "published_at", dt_from, dt_to
        ).count(),
        "downloads_in_period": _in_period(
            DownloadEvent.objects.all(), "downloaded_at", dt_from, dt_to
        ).count(),
        "by_type": by_type,
        "by_discipline": by_discipline,
    }


def recent_log_entries(limit=200):
    """Системный журнал действий (LogEntry Django) для просмотра администратором."""
    return (
        LogEntry.objects.select_related("user", "content_type").order_by("-action_time")[:limit]
    )