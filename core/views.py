from django.shortcuts import render

from dictionaries.models import Discipline


def home(request):
    disciplines = (
        Discipline.objects
        .filter(is_active=True)
        .select_related("department", "department__faculty")
        .order_by("name")
    )
    return render(request, "core/home.html", {"disciplines": disciplines})