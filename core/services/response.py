from rest_framework.response import Response

from core.domain.domain import ResponseSchema


def error_response(data, status_code=400):
    return Response(status=status_code, data=ResponseSchema(status=False, data=data).model_dump())


def success_response(data, status_code=200):
    return Response(status=status_code, data=ResponseSchema(status=True, data=data).model_dump())
