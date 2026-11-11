from django import forms

from core.forms import BootstrapFormMixin

from .models import Comment, Review


class ReviewForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Review
        fields = ("score", "text")
        widgets = {
            "score": forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            "text": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["score"].label = "Оценка (1–5)"
        self.fields["text"].label = "Комментарий к оценке (необязательно)"
        self.fields["text"].required = False


class CommentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["body"].label = "Комментарий"