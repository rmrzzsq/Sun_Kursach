from django.urls import path

from . import views

app_name = "materials"

urlpatterns = [
    path("upload/", views.MaterialUploadView.as_view(), name="upload"),
    path("my/", views.MyMaterialsView.as_view(), name="my_materials"),
    path(
        "<int:material_pk>/files/<int:file_pk>/download/",
        views.MaterialFileDownloadView.as_view(),
        name="file_download",
    ),
    path("<int:pk>/archive/", views.MaterialArchiveView.as_view(), name="archive"),
    path("", views.MaterialListView.as_view(), name="list"),
]