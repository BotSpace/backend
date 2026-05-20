"""Tests for the global DRF exception handler shape."""

from rest_framework import exceptions

from core.apps.shared.exceptions import custom_exception_handler


def test_validation_error_wrapped():
    response = custom_exception_handler(
        exceptions.ValidationError({"phone": ["This field is required."]}),
        context={},
    )
    body = response.data
    assert body["status"] is False
    assert "errors" in body
    assert body["errors"]["phone"] == ["This field is required."]


def test_not_found_wrapped():
    response = custom_exception_handler(exceptions.NotFound(), context={})
    body = response.data
    assert body["status"] is False
    assert "detail" in body


def test_permission_denied_wrapped():
    response = custom_exception_handler(exceptions.PermissionDenied("Nope"), context={})
    assert response.status_code == 403
    assert response.data["status"] is False
    assert response.data["detail"] == "Nope"


def test_unhandled_exception_returns_incident_id():
    response = custom_exception_handler(RuntimeError("boom"), context={})
    assert response.status_code == 500
    body = response.data
    assert body["status"] is False
    assert "incident_id" in body
    assert len(body["incident_id"]) == 12
    # Stack traces must NOT leak to the client.
    assert "boom" not in str(body).lower()
