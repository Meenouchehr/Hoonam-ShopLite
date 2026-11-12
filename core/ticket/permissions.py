from rest_framework import permissions
from app.models import *


class IsSuperUser(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.pk:
            if request.user.is_superuser:
                return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.pk:
            if request.user.is_superuser:
                return True
        return False


class IsSuperUserOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.pk:
            if request.user.is_superuser:
                return True
            else:
                try:
                    _user = request.user
                    _roles_qs = RoleModel.objects.filter(role_user__user=_user)
                    _roles_list = [role.pk for role in _roles_qs]
                    if "admin" in _roles_list:
                        return True
                except:
                    pass

        return False

    def has_object_permission(self, request, view, obj):
        if request.user.pk:
            if request.user.is_superuser:
                return True
            else:
                _user = request.user
                _roles_qs = RoleModel.objects.filter(role_user__user=_user)
                _roles_list = [role.pk for role in _roles_qs]
                if "admin" in _roles_list:
                    return True
        return False


class IsAdminOrPersonnel(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.pk:
            if request.user.is_superuser:
                return True
            else:
                try:
                    _user = request.user
                    _roles_qs = RoleModel.objects.filter(role_user__user=_user)
                    _roles_list = [role.pk for role in _roles_qs]
                    if "personnel" in _roles_list:  # 'admin' or 'personnel'
                        return True
                except:
                    pass
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.pk:
            if request.user.is_superuser:
                return True
            else:
                try:
                    _user = request.user
                    _roles_qs = RoleModel.objects.filter(role_user__user=_user)
                    _roles_list = [role.pk for role in _roles_qs]
                    if "personnel" in _roles_list:  # 'admin' or 'personnel'
                        return True
                except:
                    pass
        return False
