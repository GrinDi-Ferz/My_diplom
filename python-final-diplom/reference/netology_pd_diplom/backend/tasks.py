from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import yaml
import requests
from django.db import transaction
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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_order_update(self, user_email, order_status, order_id=None):
    """
    Асинхронное уведомление об обновлении статуса заказа.
    Параметры:
    - user_email: адрес получателя
    - order_status: новый статус заказа
    - order_id: идентификатор заказа (опционально)
    """
    subject = "Обновление статуса заказа"
    order_ref = f"Заказ №{order_id}" if order_id else "Ваш заказ"
    message = (
        f"Уважаемый клиент,\n\n"
        f"{order_ref} обновлён.\n"
        f"Новый статус: {order_status}.\n\n"
        "Спасибо за покупку."
    )

    try:
        _send_email(subject, user_email, message)
    except Exception as exc:
        logger.exception("Не удалось отправить письмо об обновлении статуса заказа для %s", user_email)
        raise self.retry(exc=exc)


def _save_import_to_db(shop_name, categories, goods):
    """
    Сохранение импортированных данных в БД.
    - shop_name: имя магазина из YAML
    - categories: список dicts {'id': внешн_id, 'name': str}
    - goods: список dictов с полями: id, category (external_id), name, model, price, price_rrc, quantity, parameters
    """
    # Импорт моделей внутри функции, чтобы избежать циклических импортов на старте
    from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter

    with transaction.atomic():
        shop, _ = Shop.objects.get_or_create(name=shop_name or "Unnamed Shop")

        extid_to_category = {}
        for cat in categories or []:
            external_id = cat.get('id')
            name = cat.get('name')
            if not name:
                continue
            category_obj, _ = Category.objects.get_or_create(name=name)
            category_obj.shops.add(shop)
            if external_id is not None:
                try:
                    extid_to_category[int(external_id)] = category_obj
                except (TypeError, ValueError):
                    # пропустим некорректный внешний id
                    pass

        for item in goods or []:
            external_id = item.get('id')
            if external_id is None:
                continue
            try:
                external_id = int(external_id)
            except (TypeError, ValueError):
                continue

            cat_key = item.get('category')
            category_obj = extid_to_category.get(cat_key) if cat_key is not None else None
            if category_obj is None:
                # Если категории нет в словаре extid_to_category, создаём категорию по имени или по формальному названию
                category_name = item.get('name') or f"Category {cat_key}"
                category_obj, _ = Category.objects.get_or_create(name=category_name)
                category_obj.shops.add(shop)

            product_name = item.get('name')
            if not product_name:
                continue

            product, _ = Product.objects.get_or_create(name=product_name, category=category_obj)

            defaults = {
                'model': item.get('model', ''),
                'quantity': int(item.get('quantity', 0)),
                'price': int(item.get('price', 0)),
                'price_rrc': int(item.get('price_rrc', 0)),
            }

            product_info_obj, _ = ProductInfo.objects.update_or_create(
                product=product,
                shop=shop,
                external_id=external_id,
                defaults=defaults
            )

            parameters = item.get('parameters', {}) or {}
            for param_name, param_value in parameters.items():
                parameter_obj, _ = Parameter.objects.get_or_create(name=str(param_name))
                ProductParameter.objects.update_or_create(
                    product_info=product_info_obj,
                    parameter=parameter_obj,
                    defaults={'value': str(param_value)}
                )

        return True