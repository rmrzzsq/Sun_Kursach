from django.urls import path

from . import views

app_name = "moderation"

urlpatterns = [
    path("", views.ModerationQueueView.as_view(), name="queue"),
    path("<int:pk>/", views.ModerationReviewView.as_view(), name="review"),
    path("<int:pk>/files/<int:file_pk>/download/", views.ModerationFileDownloadView.as_view(), name="file_download"),
    path("complaints/", views.ComplaintQueueView.as_view(), name="complaint_queue"),
    path("complaints/<int:pk>/", views.ComplaintReviewView.as_view(), name="complaint_review"),
]