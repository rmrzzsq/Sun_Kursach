from django.urls import path

from . import views

app_name = "feedback"

urlpatterns = [
    path("complaints/<int:material_pk>/", views.ComplaintSubmitView.as_view(), name="submit_complaint"),
]