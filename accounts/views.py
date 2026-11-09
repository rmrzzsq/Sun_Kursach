from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.db.models import Count, Q, Sum

from feedback.models import Review
from materials.models import Material
from .forms import LoginForm, ProfileForm, SignUpForm, StudySwapPasswordChangeForm


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("core:home")


class UserLoginView(LoginView):
    form_class = LoginForm
    template_name = "accounts/login.html"


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("core:home")

class ProfileUpdateView(UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        agg = Material.objects.filter(author=user).aggregate(
            total=Count("id"),
            published=Count("id", filter=Q(status="PUBLISHED")),
            downloads=Sum("download_count"),
        )
        review_agg = Review.objects.filter(
            material__author=user,
            material__published_at__isnull=False,
        ).aggregate(cnt=Count("id"))
        context["stats"] = {
            "total": agg["total"] or 0,
            "published": agg["published"] or 0,
            "downloads": agg["downloads"] or 0,
            "review_count": review_agg["cnt"] or 0,
            "rating": user.author_rating,
            "balance": user.author_balance,
        }
        return context

    def form_valid(self, form):
        from django.contrib import messages
        messages.success(self.request, "Данные профиля обновлены.")
        return super().form_valid(form)


class StudySwapPasswordChangeView(PasswordChangeView):
    form_class = StudySwapPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        from django.contrib import messages
        messages.success(self.request, "Пароль изменён.")
        return super().form_valid(form)