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


