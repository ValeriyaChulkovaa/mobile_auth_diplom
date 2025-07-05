from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.views.generic import TemplateView, ListView, FormView
from users.models import User
from authapp.forms import InviteCodeForm
from django.contrib import messages
from django.urls import reverse_lazy


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "authapp/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Получаем всех пользователей, которые указали текущего пользователя как пригласившего
        invited_users = User.objects.filter(invited_by=user)
        invited_users_count = invited_users.count()

        # Добавляем в контекст для отладки
        context["invited_users"] = invited_users
        context["user"] = user
        context["invited_users_count"] = invited_users_count
        return context


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = "authapp/user_list.html"

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        return HttpResponseForbidden(
            "Вы не можете просматривать/изменять или удалять этот объект."
        )


class EnterInviteCodeView(LoginRequiredMixin, FormView):
    template_name = "authapp/invite_code.html"
    form_class = InviteCodeForm
    success_url = reverse_lazy("authapp:index")

    def form_valid(self, form):
        invite_code = form.cleaned_data["invite_code"]
        user = self.request.user

        # Проверяем, не использовал ли пользователь уже инвайт-код
        if user.invited_by:
            messages.error(self.request, "Вы уже использовали инвайт-код")
            return self.form_invalid(form)

        # Проверяем, существует ли пользователь с таким инвайт-кодом
        try:
            invited_by_user = User.objects.get(invite_code=invite_code)
        except User.DoesNotExist:
            messages.error(self.request, "Неверный инвайт-код")
            return self.form_invalid(form)

        # Проверяем, не пытается ли пользователь использовать свой собственный инвайт-код
        if invited_by_user == user:
            messages.error(
                self.request, "Вы не можете использовать свой собственный инвайт-код"
            )
            return self.form_invalid(form)

        # Устанавливаем пригласившего пользователя
        user.invited_by = invited_by_user
        user.save()

        messages.success(self.request, "Инвайт-код успешно применен")
        return super().form_valid(form)
