from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from django.urls import reverse


import logging

logger = logging.getLogger(__name__)
