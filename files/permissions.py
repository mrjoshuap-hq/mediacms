from rest_framework import permissions

from .methods import is_mediacms_editor, is_mediacms_manager, user_is_pending_approval


class IsMediacmsEditor(permissions.BasePermission):
    def has_permission(self, request, view):
        if user_is_pending_approval(request.user):
            return False
        if is_mediacms_editor(request.user):
            return True
        return False


class IsMediacmsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        if user_is_pending_approval(request.user):
            return False
        if is_mediacms_manager(request.user):
            return True
        return False
