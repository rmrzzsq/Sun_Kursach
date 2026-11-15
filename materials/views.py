from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.encoding import escape_uri_path
from django.views import View
from django.db.models import Q
from django.views.generic import DetailView, ListView
from urllib.parse import urlencode
from dictionaries.models import Discipline, MaterialType, Teacher

from core.enums import MaterialStatus

from .forms import MaterialUploadForm
from .models import DownloadEvent, Material, MaterialFile, Tag
from .services import record_download, store_material_files

def _normalize_search(value) -> str:
    """Схлопывает repr-мусор вида ['...'] в пустую строку, разрывая цикл накопления.

    Принимает str/list/tuple/None: QueryDict-производные иногда дают список
    значений, а не строку. Легитимный поиск учебных материалов квадратных
    обёрток не содержит; при сомнении пользователь переформулирует запрос.
    """
    if isinstance(value, (list, tuple)):
        value = value[-1] if value else ""
    v = (value or "").strip()
    if v.startswith("[") and v.endswith("]"):
        return ""
    return v

class MaterialUploadView(LoginRequiredMixin, View):
    template_name = "materials/upload.html"

    def get(self, request):
        form = MaterialUploadForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = MaterialUploadForm(request.POST)
        files = request.FILES.getlist("files")

        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        material = form.save(commit=False)
        material.author = request.user
        material.status = Material.Status.MODERATION if hasattr(Material, "Status") else "MODERATION"
        material.save()

        # теги
        raw_tags = form.cleaned_data.get("tags_input", "")
        tag_names = [t.strip() for t in raw_tags.split(",") if t.strip()]
        if tag_names:
            tags = [Tag.objects.get_or_create(name=n)[0] for n in tag_names]
            material.tags.set(tags)

        errors = store_material_files(material, files)
        if errors:
            material.delete()  # откат черновика без файлов (физическое удаление запрещено только для опубликованных)
            for err in errors:
                form.add_error(None, err)
            return render(request, self.template_name, {"form": form})

        messages.success(request, "Материал отправлен на модерацию.")
        return redirect("materials:my_materials")


class MyMaterialsView(LoginRequiredMixin, View):
    template_name = "materials/my_materials.html"

    def get(self, request):
        materials = (
            Material.objects
            .filter(author=request.user)
            .prefetch_related("files")
            .order_by("-created_at")
        )
        return render(request, self.template_name, {"materials": materials})


class MaterialFileDownloadView(LoginRequiredMixin, View):
    def get(self, request, material_pk, file_pk):
        material = get_object_or_404(Material, pk=material_pk)
        file = get_object_or_404(MaterialFile, pk=file_pk, material=material)

        # Скачивание разрешено только опубликованных материалов.
        if material.status != "PUBLISHED":
            raise Http404("Файл недоступен для скачивания.")

        record_download(material, file, request.user)

        response = FileResponse(
            file.file.open("rb"),
            as_attachment=True,
            filename=file.original_name,
        )
        # Корректная передача имени файла с кириллицей/пробелами.
        response["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{escape_uri_path(file.original_name)}"
        )
        return response
    
class MaterialArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        material = get_object_or_404(
            Material, pk=pk, author=request.user, status=MaterialStatus.PUBLISHED
        )
        material.status = MaterialStatus.ARCHIVED
        material.save()
        messages.success(request, "Материал переведён в архив.")
        return redirect("materials:my_materials")

class MaterialListView(ListView):
    model = Material
    template_name = "materials/list.html"
    context_object_name = "materials"
    paginate_by = 20

    def _params(self):
        params = self.request.GET.dict()
        params["mat_q"] = _normalize_search(params.get("mat_q", ""))
        params["mat_tags"] = _normalize_search(params.get("mat_tags", ""))
        return params

    def get_queryset(self):
        qs = (
            Material.objects
            .filter(status=MaterialStatus.PUBLISHED)
            .select_related("author", "discipline", "teacher", "type")
            .prefetch_related("tags")
            .order_by("-published_at", "-created_at")
        )
        p = self._params()
        if p.get("discipline"):
            qs = qs.filter(discipline_id=p["discipline"])
        if p.get("teacher"):
            qs = qs.filter(teacher_id=p["teacher"])
        if p.get("type"):
            qs = qs.filter(type_id=p["type"])
        if p.get("semester"):
            qs = qs.filter(semester=p["semester"])
        if p.get("year"):
            qs = qs.filter(academic_year=p["year"])
        tag_names = [t.strip() for t in p.get("mat_tags", "").split(",") if t.strip()]
        if tag_names:
            qs = qs.filter(tags__name__in=tag_names).distinct()
        q = p.get("mat_q", "")
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(author__full_name__icontains=q)
                | Q(author__email__icontains=q)
            ).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self._params()
        ctx["filters"] = params
        ctx["disciplines"] = Discipline.objects.filter(is_active=True).order_by("name")
        ctx["teachers"] = Teacher.objects.filter(is_active=True).order_by("full_name")
        ctx["types"] = MaterialType.objects.filter(is_active=True).order_by("name")
        ctx["semesters"] = range(1, 9)
        ctx["years"] = (
            Material.objects.filter(status=MaterialStatus.PUBLISHED)
            .values_list("academic_year", flat=True)
            .distinct()
            .order_by("-academic_year")
        )
        qs_params = {k: v for k, v in params.items() if k != "page" and v != ""}
        ctx["querystring"] = urlencode(qs_params)
        return ctx

class MaterialDetailView(DetailView):
    model = Material
    template_name = "materials/detail.html"
    context_object_name = "material"

    def get_queryset(self):
        return (
            Material.objects
            .filter(status=MaterialStatus.PUBLISHED)
            .select_related("author", "discipline", "teacher", "type")
            .prefetch_related("tags", "files", "reviews__user", "comments__user")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        material = ctx["material"]
        user = self.request.user
        is_auth = user.is_authenticated
        ctx["is_auth"] = is_auth
        ctx["is_own"] = is_auth and material.author_id == user.pk
        ctx["can_download"] = is_auth
        ctx["has_downloaded"] = (
            is_auth
            and DownloadEvent.objects.filter(material=material, user=user).exists()
        )
        ctx["author_reviews"] = material.reviews.select_related("user").order_by("-created_at")
        ctx["author_comments"] = material.comments.select_related("user").order_by("created_at")
        ctx["author_rating"] = material.author.author_rating
        ctx["author_balance"] = material.author.author_balance
        return ctx