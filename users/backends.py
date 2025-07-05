from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache
from users.models import User
from loguru import logger


class PhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        logger.info(f"Аутентификация на телефон: {username}, код:{password}")
        if username and password:
            user = User.objects.filter(phone=username).first()
            if user:
                logger.debug(f"Пользователь найден: {user}")
                cached_code = cache.get(f"user_{username}_code")
                logger.debug(f"Код из кэша: {cached_code}")
                if user.check_code(password) or password == cached_code:
                    logger.info("Совпадение кодов")
                    cache.delete(f"user_{username}_code")
                    return user
                else:
                    logger.info("Код не соответствует")
            else:
                logger.info("Пользователь не найден")
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
