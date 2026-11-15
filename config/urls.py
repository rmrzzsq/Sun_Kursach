from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "StudySwap | Администрация"
admin.site.site_title = "StudySwap Admin"
admin.site.index_title = "Управление системой"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("materials/", include("materials.urls")),
    path("feedback/", include("feedback.urls")),
    path("moderation/", include("moderation.urls")),
    path("reports/", include("reports.urls")),
    path("", include("core.urls")),
]