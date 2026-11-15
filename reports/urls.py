from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ActivityReportView.as_view(), name="activity"),
    path("content/", views.ContentVolumeView.as_view(), name="content"),
    path("log/", views.SystemLogView.as_view(), name="log"),
]