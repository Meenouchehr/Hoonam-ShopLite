import functools

from rest_framework.response import Response
from rest_framework import status

from django.conf import settings
from django.contrib.admin.views.decorators import user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.translation import gettext as _

from app.exceptions import ProjectException

from app.models import *
from app.helpers import *


def admin_required(view_func=None,redirect_field_name=REDIRECT_FIELD_NAME,login_url=settings.LOGIN_URL):
    """
    Decorator for views that checks that the user is logged in and is a
    superuser, redirecting to the login page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url=login_url,
        redirect_field_name=redirect_field_name)
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator

def execute_with_permission(state, operate):
    def decorator(func):
        @functools.wraps(func)
        def check_permission(self, request, *args, **kwargs):
            _user = request.user
            _chk  = False
            if _user.pk and _user.is_superuser:
                _chk = True
            if (not _chk) and _user.pk:
                access = True
                new_operate = operate
                if operate in ["list","trash"]:
                    new_operate = "read"
                elif operate in ["recycle","status",]:
                    new_operate = "update"
                elif operate in ["some"]:
                    new_operate = "delete"
                elif operate == "multi_activation":
                    new_operate = "activation"
                
                if state == "user":
                    user_id = kwargs.get('pk', None)
                    if operate in ["update","read"]:
                        if _user.pk == user_id:
                            _chk = True
                    elif operate == "delete":
                        if _user.pk == user_id:
                            _chk = False 
                            access = False   
                    elif operate in ["some","status","multi_activation"]:
                        user_ids = request.data.get('id', None)
                        if _user.pk in user_ids:
                            _chk = False
                            access = False
                elif state == "operate":
                    pass
                elif state == "state":
                    pass
                elif state == "role":
                    pass
                elif state == "userrole":
                    pass

                if access and (not _chk):
                    _roles = RoleModel.objects.filter(role_accesses__state=state,role_accesses__role_permissions__operate=new_operate).distinct()
                    if _roles:
                        user_role = UserRoleModel.objects.filter(user=_user,role__in=_roles)
                        if user_role:
                            _chk = True
            # Check:
            if _chk:
                return func(self, request, *args, **kwargs)
            elif _user.pk:
                return Response(
                    {
                        "code": _("900"),
                        "message": _("Forbidden"),
                        "detail": _("permission denid"),
                    }, status.HTTP_403_FORBIDDEN)
            else:
                return Response({"code": _("899"),"message": _("user not recognized")},
                                status.HTTP_401_UNAUTHORIZED)
        return check_permission
    return decorator

def level_required(level):
    def decorator(func):
        @functools.wraps(func)
        def decode_token(request, *args, **kwargs):
            _user = request.request.user
            list_roles    = get_user_roles()
            if _user.is_superuser or ('admin' in list_roles):
                return func(request, *args, **kwargs)
            _level  = _user.level
            if type(level) is int:
                if _level == level:
                    return func(request, *args, **kwargs)
            elif type(level) is list:
                for l in level:
                    if type(l) is int:
                        if _level==l:
                            return func(request, *args, **kwargs)

            if _level==0:
                raise ProjectException(0,'runtime error','profile information required',status.HTTP_403_FORBIDDEN)
            elif _level==1:
                raise ProjectException(0,'runtime error','profile evidence upload on required',status.HTTP_403_FORBIDDEN)
            elif _level==2:
                raise ProjectException(0,'runtime error','protector information required',status.HTTP_403_FORBIDDEN)
            elif _level==3:
                raise ProjectException(0,'runtime error','protector evidence upload on required',status.HTTP_403_FORBIDDEN)
            elif _level==4:
                raise ProjectException(0,'runtime error','payment required',status.HTTP_402_PAYMENT_REQUIRED)
            elif _level==5:
                raise ProjectException(0,'runtime error','upload video required',status.HTTP_403_FORBIDDEN)                
            elif _level==6:  
                raise ProjectException(0,'runtime error','finish',status.HTTP_410_GONE)
            
        return decode_token
    return decorator

