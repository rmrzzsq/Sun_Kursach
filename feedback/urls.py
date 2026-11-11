from django.urls import path

from . import views

app_name = "feedback"

urlpatterns = [
    path("reviews/<int:material_pk>/", views.ReviewCreateView.as_view(), name="create_review"),
    path("comments/<int:material_pk>/", views.CommentCreateView.as_view(), name="create_comment"),
    path("complaints/<int:material_pk>/", views.ComplaintSubmitView.as_view(), name="submit_complaint"),
]