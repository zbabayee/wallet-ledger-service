from django.core.exceptions import ValidationError
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        custom_response = {
            'status': 'error',
            'message': response.data.get('detail', 'Error occuted'),
            'errors': response.data
        }
        response.data = custom_response
    return response


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def validate_phone(phone):
    import re
    pattern = r'^09\d{9}$'
    if not re.match(pattern, phone):
        raise ValidationError("phone number should start with 09 and has 11 digits.")
    return phone
