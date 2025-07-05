# Mobile Authenticator

Система авторизации по номеру телефона с реферальной системой.

## Описание

Проект представляет собой систему авторизации пользователей по номеру телефона с поддержкой реферальной системы. 
Пользователи могут авторизовываться с помощью SMS кодов и использовать инвайт-коды для приглашения других пользователей.

## Функциональность

- Авторизация по номеру телефона с подтверждением через SMS
- Реферальная система с инвайт-кодами
- API для всех операций
- Веб-интерфейс для тестирования

## Требования

- Python 3.12
- PostgreSQL
- Redis (для кэширования)
- SMS Aero API ключ

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/ValeriyaChulkovaa/mobile_auth_diplom.git
cd mobile_auth_diplom
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/Mac
.venv\Scripts\activate  # для Windows
```


4. Создайте файл .env на основе .env_sample и заполните необходимые переменные:
```bash
cp .env_sample .env
```

5. Примените миграции:
```bash
python manage.py migrate
```

6. Запустите сервер:
```bash
python manage.py runserver
```

## API Endpoints

### Регистрация и авторизация

#### POST /api/register/
Регистрация нового пользователя или запрос кода подтверждения для существующего.

**Request:**
```json
{
    "phone": "+79001234567"
}
```

**Response:**
```json
{
    "message": "Код отправлен",
    "debug_code": "9378"
}
```

#### POST /api/verify-code/
Подтверждение кода авторизации.

**Request:**
```json
{
    "phone": "+79001234567",
    "code": "9378"
}
```

**Response:**
```json
{
    "refresh": "refresh_token",
    "access": "access_token"
}
```

### Профиль пользователя

#### GET /api/profile/
Получение информации о текущем пользователе.

**Request:**
```json
{
    "phone": "+79001234567"
}
```

**Response:**
```json
{
    "id": 1,
    "phone": "+79001234567",
    "invite_code": "ABC123",
    "invited_by_user": {
        "id": 2,
        "phone": "+79007654321",
        "invite_code": "XYZ789"
    },
    "created_at": "2024-03-12T12:00:00Z",
    "invited_users": [
        {
            "id": 3,
            "phone": "+79009876543"
        }
    ]
}
```

#### GET /api/profile/
Получение access_token с помощью refresh_token.

**Request:**
```json
{
    "refresh": "refresh_token"
}
```


**Response:**
```json
{
    "access": "access_token"
}
```

## Тестирование

В settings.py DEBUG = True - включено тестовая отправка SMS через сервис SMSAero, с помощью метода ```sms/testsend```.  
Метод тестовой отправки сообщения используется для отладки запросов к API.  
Вы можете выключить режим отладки изменив в settings.py DEBUG = False - тогда сервис будет отправлять SMS с помощью метода ```sms/send``` на телефон, взимая плату.  

Для запуска тестов выполните:
```bash
python manage.py test
```

## Документация API

Подробная документация API доступна по адресу `redoc/` после запуска сервера.

## Postman Collection

Postman коллекция для тестирования API доступна в файле `MobileAuthenticator.postman_collection.json`. 
