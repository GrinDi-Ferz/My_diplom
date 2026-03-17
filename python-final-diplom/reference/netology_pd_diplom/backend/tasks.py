from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def _send_email(subject: str, to_email: str, message: str) -> int:
    """
    Вспомогательная функция отправки письма.
    Возвращает число отправленных писем (обычно 1 или 0).
    """
    try:
        return send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [to_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception("Не удалось отправить письмо по адресу %s: %s", to_email, exc)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, user_email, user_name, token):
    """
    Асинхронная отправка письма со сбросом пароля.
    Параметры:
    - user_email: адрес получателя
    - user_name: имя пользователя (для контекста в тексте письма)
    - token: токен сброса
    """
    subject = f"Сброс пароля для {user_name}"
    lines = [
        f"Здравствуйте, {user_name},",
        "",
        f"Используйте следующий код для сброса пароля: {token}",
    ]
    lines += [
        "",
        "Если вы не запрашивали сброс пароля, проигнорируйте это письмо.",
    ]
    message = "\n".join(lines)

    try:
        _send_email(subject, user_email, message)
    except Exception as exc:
        logger.exception("Не удалось отправить письмо с сбросом пароля по адресу %s", user_email)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_confirm_email(self, user_email, token_key, user_name=None):
    """
    Асинхронная отправка письма с подтверждением электронной почты.
    Параметры:
    - user_email: адрес получателя
    - token_key: ключ токена подтверждения
    - user_name: имя пользователя (необязательно)
    """
    subject = "Подтверждение адреса электронной почты"
    name = user_name or user_email
    message = (
        f"Здравствуйте, {name},\n\n"
        f"Ваш токен подтверждения адреса: {token_key}\n\n"
        "Пожалуйста, используйте этот токен для подтверждения адреса.\n"
        "Если вы не запрашивали подтверждение, проигнорируйте это письмо."
    )

    try:
        _send_email(subject, user_email, message)
    except Exception as exc:
        logger.exception("Не удалось отправить письмо с подтверждением на %s", user_email)
        raise self.retry(exc=exc)