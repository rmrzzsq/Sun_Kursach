from django import forms

# Класс Bootstrap 5 по типу виджета. Неизвестные виджеты (например, HiddenInput)
# намеренно не трогаем — не хотим ломать их служебную разметку.
_BOOTSTRAP_CLASS_BY_WIDGET = {
    forms.TextInput: "form-control",
    forms.EmailInput: "form-control",
    forms.URLInput: "form-control",
    forms.NumberInput: "form-control",
    forms.Textarea: "form-control",
    forms.PasswordInput: "form-control",
    forms.FileInput: "form-control",
    forms.ClearableFileInput: "form-control",
    forms.Select: "form-select",
    forms.SelectMultiple: "form-select",
    forms.CheckboxInput: "form-check-input",
    forms.CheckboxSelectMultiple: "form-check-input",
    forms.RadioSelect: "form-check-input",
}


class BootstrapFormMixin:
    """Применяет CSS-классы Bootstrap к виджетам формы в __init__.

    Миксин обязан стоять ПЕРВЫМ в списке базовых классов, чтобы его __init__
    выполнился после построения self.fields родительским ModelForm и смог
    пройтись по всем полям (включая автоматически добавленные password1/2).
    Идемпотентен: повторный вызов не дублирует класс.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            cls = _BOOTSTRAP_CLASS_BY_WIDGET.get(type(field.widget))
            if not cls:
                continue
            existing = field.widget.attrs.get("class", "")
            if cls not in existing.split():
                field.widget.attrs["class"] = f"{existing} {cls}".strip()