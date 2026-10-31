import logging
from django.db.models.deletion import ProtectedError
from rest_framework import permissions, status
from rest_framework.exceptions import APIException
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.throttling import SimpleRateThrottle


class Pagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsTrainer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == 'trainer')


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'The external service is unavailable. Please try again later.'


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT


class ScopedUserThrottle(SimpleRateThrottle):
    scope = 'ai'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': request.user.pk if request.user.is_authenticated else self.get_ident(request)}


class AIThrottle(ScopedUserThrottle):
    scope = 'ai'


class CodeThrottle(ScopedUserThrottle):
    scope = 'code'


class AuthThrottle(ScopedUserThrottle):
    scope = 'auth'


def exception_handler(exc, context):
    if isinstance(exc, ProtectedError):
        return Response({'detail': 'This record has dependent records. Deactivate or archive it instead.'}, status=409)
    response = drf_exception_handler(exc, context)
    if response is None:
        logging.getLogger('skillforge').error('Request failed: %s', type(exc).__name__)
        return Response({'detail': 'An internal error occurred. Please retry or contact your trainer.'}, status=500)
    return response
