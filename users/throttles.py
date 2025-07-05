from rest_framework.throttling import AnonRateThrottle


class PhoneCodeThrottle(AnonRateThrottle):
    rate = "100/hour"  # 100 запроса в час на номер


class VerifyCodeThrottle(AnonRateThrottle):
    rate = "30/minute"  # 5 попыток ввода кода в минуту
