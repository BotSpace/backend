# type: ignore
from drf_spectacular.utils import OpenApiExample, OpenApiRequest, OpenApiResponse, extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.apps.payment.serializers.payment.payment import CreatePaymentLinkSerializer
from core.domain.ws import ResponseSchema


@extend_schema(
    tags=["order"],
    request=CreatePaymentLinkSerializer,
    examples=[
        OpenApiExample(
            name="create",
            value={"method": "click", "order": 10},
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
    order = data.get("order")
    return Response(data=ResponseSchema(data={"link": "https://google.com/%s/%s" % (method, order.pk)}).model_dump())
