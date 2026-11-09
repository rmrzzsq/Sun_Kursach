from django import forms

from dictionaries.models import Discipline, MaterialType, Teacher

from .models import Material


class MaterialUploadForm(forms.ModelForm):
    tags_input = forms.CharField(
        label="Теги (через запятую)",
        required=False,
        help_text="Например: графы, матлогика, экзамен",
    )

    class Meta:
        model = Material
        fields = (
            "title",
            "description",
            "discipline",
            "teacher",
            "type",
            "semester",
            "academic_year",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["discipline"].queryset = Discipline.objects.filter(is_active=True)
        self.fields["teacher"].queryset = Teacher.objects.filter(is_active=True)
        self.fields["type"].queryset = MaterialType.objects.filter(is_active=True)
        self.fields["title"].label = "Название материала"
        self.fields["description"].label = "Описание"
        self.fields["discipline"].label = "Дисциплина"
        self.fields["teacher"].label = "Преподаватель"
        self.fields["type"].label = "Тип материала"
        self.fields["semester"].label = "Семестр"
        self.fields["academic_year"].label = "Учебный год"

    def clean_semester(self):
        value = self.cleaned_data["semester"]
        if value < 1 or value > 8:
            raise forms.ValidationError("Семестр должен быть в диапазоне 1–8.")
        return value

    def clean_academic_year(self):
        value = self.cleaned_data["academic_year"]
        if value < 2000 or value > 2100:
            raise forms.ValidationError("Укажите корректный учебный год (например, 2026).")
        return value