from rest_framework.views import exception_handler

def system_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        if _detail := response.data.pop('detail', None):
            response.data = { 'error':{ 'code':response.status_code,
                                    'message':response.status_text,
                                    'detail':_detail}}

        else:
            _error=response.data.pop('error',None)
            response.data = { 'error':_error}

    return response