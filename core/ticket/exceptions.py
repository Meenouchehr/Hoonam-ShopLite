from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


from rest_framework import status


class TicketException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = 500
    default_detail = "A server error occurred."
    default_message = "A server error occurred."

    def __init__(self, code, message, detail, status_code):
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.default_code = code
        if detail is not None:
            self.default_detail = detail
        if message is not None:
            self.default_message = message
        self.detail = {
            "error": {
                "code": self.default_code,
                "message": self.default_message,
                "detail": self.default_detail,
            }
        }


def system_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        _detail = response.data.pop("detail", None)
        if not _detail:
            _error = response.data.pop("error", None)
            response.data = {"error": _error}

        else:
            response.data = {
                "error": {
                    "code": response.status_code,
                    "message": response.status_text,
                    "detail": _detail,
                }
            }

    return response
