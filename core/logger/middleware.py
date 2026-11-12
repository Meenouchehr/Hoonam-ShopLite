from datetime import datetime
from logger.serializers import LogSerializer
import json

class BaseMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

class ProcessViewNoneMiddleware(BaseMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
       
        # _authorization=request.headers.get('Authorization',None)
        # _method=request.META.get('REQUEST_METHOD',None)
        # _forward=request.META.get('PATH_INFO',None)
        _body={}
        try:
            _body=request.body.decode('utf-8').strip()
        except:
            _body=request.body.strip()
        
        # _data={'authorization':_authorization,'function':_function,'method':_method,'forwarded':_forward,'body':_body}
        # _serializer=LogSerializer(data=_data)
        # if _serializer.is_valid():
        #     _serializer.save() 
        return None
    
    def process_exception(self,request, exception):
        #intitle = u'{}: {}'.format(exception.__class__.__name__,  exception.message)

        _authorization=request.headers.get('Authorization',None)
        _method=request.META.get('REQUEST_METHOD',None)
        _http_cookie=request.META.get('HTTP_COOKIE',None)
        _csrf_cookie=request.META.get('CSRF_COOKIE',None)
        _query_string=request.META.get('QUERY_STRING',None)
        _scheme=request.scheme
        _url=request.META.get('PATH_INFO',None)

        _body={}
        try:
            _body=request.body.decode('utf-8').strip()
        except:
            _body=request.body.strip()
            
        _function=request.resolver_match._func_path
        _data= ''
        _status_code=''
        _status_text=''
        _user=str(request.user)
        _date=datetime.utcnow().strftime('%B %d %Y - %H:%M:%S')

        _remote_addr=request.META.get('HTTP_X_REAL_IP',None)
        if not _remote_addr:
            _remote_addr=request.META.get('REMOTE_ADDR',None)
        
        _exception=exception.__class__.__name__
        _exception_data=' '.join([str(elem) for elem in list(exception.args)]) 
        _data={'authorization':_authorization,'http_cookie':_http_cookie,'csrf_cookie':_csrf_cookie,'method':_method,'function':_function,'scheme':_scheme,'url':_url,'body':_body,'query_string':_query_string,'status_code':_status_code,'status_text':_status_text,'data':_data,'user':_user,'date':_date,'address':_remote_addr,'exception':_exception,'exception_data':_exception_data}
        _serializer=LogSerializer(data=_data)
        if _serializer.is_valid():
            _serializer.save() 
        print()
        return None
    def process_template_response(self,request, response):
        _authorization=request.headers.get('Authorization',None)
        _method=request.META.get('REQUEST_METHOD',None)
        _http_cookie=request.META.get('HTTP_COOKIE',None)
        _csrf_cookie=request.META.get('CSRF_COOKIE',None)
        _query_string=request.META.get('QUERY_STRING',None)
        _scheme=request.scheme
        _url=request.META.get('PATH_INFO',None)

        _body={}
        try:
            _body=request.body.decode('utf-8').strip()
        except:
            _body=request.body.strip()
        _function=request.resolver_match._func_path
        _data= json.dumps(response.data).strip()
        _status_code=str(response.status_code).strip()
        _status_text=response.status_text.strip()
        _user=str(request.user)
        _date=datetime.utcnow().strftime('%B %d %Y - %H:%M:%S')

        _remote_addr=request.META.get('HTTP_X_REAL_IP',None)
        if not _remote_addr:
            _remote_addr=request.META.get('REMOTE_ADDR',None)

        _data={'authorization':_authorization,'http_cookie':_http_cookie,'csrf_cookie':_csrf_cookie,'method':_method,'function':_function,'scheme':_scheme,'url':_url,'body':_body,'query_string':_query_string,'status_code':_status_code,'status_text':_status_text,'data':_data,'user':_user,'date':_date,'address':_remote_addr}
        _serializer=LogSerializer(data=_data)
        if _serializer.is_valid():
            _serializer.save() 
        return response