from django_core.mixins import BaseViewSetMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from core.services.response import success_response


class BalanceView(BaseViewSetMixin, ViewSet):
    permission_classes = [IsAuthenticated]

    def get_balance(self, request):
        """User hisobidagi balansni olish

        Args:
            request ([TODO:type]): [TODO:description]
        """
        return Response(data={"balance": request.user.balance}, status=200)
