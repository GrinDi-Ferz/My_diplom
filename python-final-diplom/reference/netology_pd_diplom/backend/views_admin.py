from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from django.urls import reverse


import logging

logger = logging.getLogger(__name__)

try:
    from .tasks import do_import
except Exception:
    do_import = None  # на этапе разработки может быть заглушка

class DoImportTriggerAPIView(APIView):
    """
    Админская точка входа для запуска Celery задачи do_import из админки.
    Доступ: IsAdminUser
    Принимает JSON: {"source_url": "<URL>"}.
    Возвращает task_id и URL для проверки статуса задачи.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        if do_import is None:
            return Response({"error": "Задача не сконфигурирована"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        source_url = request.data.get("source_url")
        if not source_url:
            return Response({"error": "Поле 'source_url' обязательно."}, status=status.HTTP_400_BAD_REQUEST)

        # Запуск Celery задачи
        try:
            result = do_import.delay(source_url)
        except Exception as exc:
            logger.exception("Не удалось запустить задачу do_import: %s", exc)
            return Response({"error": "Не удалось запустить задачу импорта", "detail": str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        status_url = request.build_absolute_uri(
            reverse("admin_do_import_status", kwargs={"task_id": str(result.id)})
        )
        return Response({
            "task_id": str(result.id),
            "status_url": status_url
        }, status=status.HTTP_202_ACCEPTED)


class DoImportStatusAPIView(APIView):
    """
    Проверка статуса задачи do_import по task_id.
    Доступ: IsAdminUser
    Метод GET: /admin/do_import/status/<task_id>/
    """
    permission_classes = [IsAdminUser]

    def get(self, request, task_id, *args, **kwargs):
        result = AsyncResult(task_id)
        data = {
            "task_id": task_id,
            "status": result.status
        }
        if result.ready():
            try:
                data["result"] = result.get()
            except Exception as exc:
                data["error"] = str(exc)
        return Response(data)