# type: ingore
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication


class IsAuthOrEngine(BasePermission):
    def has_permission(self, request, view):
        auth = JWTAuthentication()
        try:
            res = auth.authenticate(request)
            if res is None:
                return False
            user, token = res
        except Exception:
            return False

        if not user:
            return False
        role = token.get("role", None)
        if role == "admin":
            return True

        return False
