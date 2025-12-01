from payme.views import PaymeWebHookAPIView
from rest_framework.permissions import AllowAny

class PaymeCallBackAPIView(PaymeWebHookAPIView):
    permission_classes = [AllowAny]


    def handle_successfully_payment(self, params, result, *args, **kwargs):
        """
        Handle the successful payment. You can override this method
        """
        print(f"Transaction successfully performed for this params: {params} and performed_result: {result}")

    def handle_cancelled_payment(self, params, result, *args, **kwargs):
        """
        Handle the cancelled payment. You can override this method
        """
        print(f"Transaction cancelled for this params: {params} and cancelled_result: {result}")