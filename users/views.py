from users.services import send_sms
from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny

from django.views.generic import View, FormView
from django.contrib import messages
from users.models import User
from users.serializers import UserSerializer, RegisterSerializer, VerifyCodeSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from smsaero import SmsAeroException

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from users.forms import PhoneLoginForm, CodeForm
from loguru import logger
from config.settings import DEBUG
from users.throttles import PhoneCodeThrottle, VerifyCodeThrottle


class RegisterView(APIView):
    """
    Эндпоинт для логина в сервис, присваивания инвайт-кода.
    Ожидает номер телефона.
    В случае успеха, отправляет код.
    """
    permission_classes = [AllowAny]
    throttle_classes = [PhoneCodeThrottle]  # Ограничение запросов

    @swagger_auto_schema(
        request_body=RegisterSerializer,
        responses={
            200: "Код отправлен",
            400: "Ошибка валидации",
            500: "Ошибка отправки SMS"
        }
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data["phone"]
            invited_by_code = serializer.validated_data.get("invited_by")

            # Проверяем, существует ли пользователь с таким номером
            user, created = User.objects.get_or_create(phone=phone)

            if not created:
                if user.invited_by and invited_by_code:
                    return Response(
                        {
                            "invited_by": "Инвайт-код уже указан и не может быть изменён."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Устанавливаем инвайт-код, если он передан и ранее не был установлен
            if invited_by_code and not user.invited_by:
                invited_by_user = User.objects.filter(
                    invite_code=invited_by_code
                ).first()
                if invited_by_user:
                    user.invited_by = invited_by_user
                    user.save()

            # Отправляем код подтверждения
            try:
                message_code = user.generate_code()
                code = send_sms(phone, message_code)
                logger.debug(
                    f"Логин на телефон: {phone}. "
                    f"Код подтверждения: {message_code}."
                )
                if code:
                    response_data = {"message": "Код отправлен"}
                    if DEBUG:
                        response_data["debug_code"] = message_code
                    return Response(response_data, status=status.HTTP_200_OK)
            except SmsAeroException:
                return Response(
                    {"message": "Ошибка отправки SMS. Попробуйте позже."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyCodeView(APIView):
    """
    Эндпоинт для проверки кода подтверждения.
    Ожидает номер телефона и код подтверждения.
    Проверяет корректность кода и, в случае успеха, выдаёт JWT-токены.
    """

    permission_classes = [AllowAny]
    throttle_classes = [VerifyCodeThrottle]

    @swagger_auto_schema(
        request_body=VerifyCodeSerializer,
        responses={
            200: "Авторизация успешна",
            400: "Ошибка валидации",
            403: "Неверный код",
        }
    )
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data["phone"]
            code = serializer.validated_data["code"]
            user = User.objects.filter(phone=phone).first()
            if user and user.check_code(code):
                # Генерация JWT токенов
                refresh = RefreshToken.for_user(user)
                return Response(
                    {"refresh": str(refresh), "access": str(refresh.access_token)},
                    status=status.HTTP_200_OK,
                )
                return Response(
                    {"message": "Авторизация успешна"}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"message": "Неверный код или срок действия истек"}, status=status.HTTP_403_FORBIDDEN
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveAPIView):
    """
    Эндпоинт для получения информации о пользователе.
    Ожидает access_token.
    После чего выдает информации о пользователе
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class PhoneLoginView(View):
    """Эндпоинт для входа в сервис(html)."""
    template_name = "users/phone_login.html"
    form_class = PhoneLoginForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone"]
            request.session["phone"] = phone
            user, created = User.objects.get_or_create(
                phone=phone
            )  # Получаем или создаем пользователя
            code = user.generate_code()  # Генерация кода

            # Сохраняем код в кэш
            # cache.set(f"user_{phone}_code", code, 300)  # 300 секунд = 5 минут

            try:
                send_sms(phone, code)
                # messages.success(request, "Код подтверждения отправлен")
                return redirect("authapp:phone_confirm")
            except Exception as e:
                messages.error(request, f"Ошибка отправки SMS: {str(e)}")
                return render(request, self.template_name, {"form": form})

        return render(request, self.template_name, {"form": form})


class PhoneConfirmView(FormView):
    """Эндпоинт для подтверждения входа в сервис(html)."""
    template_name = "users/phone_confirm.html"
    form_class = CodeForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        phone = self.request.session.get("phone")
        if phone:
            cached_code = cache.get(f"user_{phone}_code")
            logger.debug(
                f"Логин на телефон: {phone}. "  
                f"Код подтверждения: {cached_code}."
            )
            context["cached_code"] = cached_code
            context["debug"] = DEBUG  # для html
        return context

    def post(self, request, *args, **kwargs):
        phone = request.session.get("phone")
        code = request.POST.get("code")

        if not phone:
            messages.error(
                request, "Сессия истекла. Пожалуйста, введите номер телефона заново."
            )
            return redirect("users:phone_login")

        user = User.objects.filter(phone=phone).first()
        cached_code = cache.get(f"user_{phone}_code")

        if user and (user.check_code(code) or code == cached_code):
            # Очищаем код из кэша после успешной авторизации
            # cache.delete(f"user_{phone}_code")
            user = authenticate(request=request, username=phone, password=code)
            # print(f"телефон сессии: {phone}")
            # print(f"код формы: {code}")
            # print(user)
            if user is not None:
                cache.delete(f"user_{phone}_code")
                login(request, user, backend="users.backends.PhoneBackend")
                return redirect("authapp:index")
            else:
                form = self.get_form()
                form.add_error("code", "Неверный код")
                return self.form_invalid(form)
