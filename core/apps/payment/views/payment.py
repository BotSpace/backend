# type: ignore
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from config.env import env
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.apps.payment.models.transaction import TransactionModel
from core.apps.payment.serializers.payment.payment import CreatePaymentLinkSerializer
from core.domain import ResponseSchema
from click_up import ClickUp


@extend_schema(
    tags=["order"],
    request=CreatePaymentLinkSerializer,
    examples=[
        OpenApiExample(
            name="create",
            value={"method": "click", "amount": 100000},
            request_only=True,
        )
    ],
    responses={
        200: OpenApiResponse(
            response={
                "type": "object",
                "properties": {
                    "link": {
                        "type": "string",
                        "example": "https://google.com",
                    },
                },
            }
        ),
    },
)
@api_view(["POST"])
def payment_link(request):
    serializer = CreatePaymentLinkSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(data={"detail": ResponseSchema(data=serializer.errors).model_dump()})
    data = serializer.validated_data
    method = data.get("method")
    amount = data.get("amount")
    transaction = TransactionModel.objects.create(user=request.user, amount=amount)
    paylink = ""
    if method == "click":
        click_up = ClickUp(service_id=env.str("CLICK_SERVICE_ID"), merchant_id=env.str("CLICK_MERCHANT_ID"))
        paylink = click_up.initializer.generate_pay_link(
            id=transaction.pk,
            amount=amount,
            return_url="https://botmother.uz",
        )
    elif method == "payme":
        paylink = "https://payme.uz"
    return Response(data=ResponseSchema(data={"link": paylink}).model_dump())
