"""OAuth2 credential endpoints.

POST /api/v1/credentials/oauth/<provider>/start/   — authenticated; returns authorize_url
GET  /api/v1/credentials/oauth/<provider>/callback/ — AllowAny; Google redirects here
"""
from __future__ import annotations

from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core import signing
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.credentials.models import Credential
from core.apps.credentials.oauth_providers import get_provider
from core.apps.credentials.registry import get_type
from core.apps.credentials.services import crypto
from core.apps.credentials.services.oauth import (
    CALLBACK_URL,
    build_token_data,
    exchange_code,
    fetch_userinfo,
    make_state,
    verify_state,
)

User = get_user_model()

_PANEL_URL = "https://admin.botspace.uz"

_SUCCESS_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Connected</title></head>
<body>
<p>Connected! This window will close automatically.</p>
<p>If it doesn't, <a href="{panel_url}">return to the panel</a>.</p>
<script>
try {{
  window.opener.postMessage({{type:'credential-oauth',ok:true,provider:'{provider}'}}, '*');
  window.close();
}} catch(e) {{}}
</script>
</body>
</html>"""

_ERROR_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Error</title></head>
<body>
<p>Authentication failed: {error}</p>
<p><a href="{panel_url}">Return to the panel</a>.</p>
<script>
try {{
  window.opener.postMessage({{type:'credential-oauth',ok:false,error:{error_json},provider:'{provider}'}}, '*');
  window.close();
}} catch(e) {{}}
</script>
</body>
</html>"""


def _error_html(provider: str, error: str) -> HttpResponse:
    import json
    body = _ERROR_HTML.format(
        error=error,
        error_json=json.dumps(error),
        provider=provider,
        panel_url=_PANEL_URL,
    )
    return HttpResponse(body, status=400, content_type="text/html; charset=utf-8")


def _upsert_credential(owner_id: int, type_key: str, token_data: dict) -> Credential:
    """Create or update oauth2 credential for this owner + type_key."""
    type_info = get_type(type_key) or {}
    account_email = token_data.get("account_email", "")
    default_label = type_info.get("label", type_key)

    encrypted = crypto.encrypt(token_data)

    # Upsert: find existing (not deleted) by owner + type_key, or create new
    existing = Credential.objects.filter(
        owner_id=owner_id, type_key=type_key, deleted_at__isnull=True
    ).first()

    if existing:
        # Re-connect: only refresh the tokens. Keep the existing (possibly user-edited)
        # name so we never clobber a rename or collide on (owner, name).
        existing.data_encrypted = encrypted
        existing.save(update_fields=["data_encrypted", "updated_at"])
        return existing

    # New credential: a meaningful, de-duplicated default name. Include the type label so the
    # same Google account used for different types (email/sheets/drive) doesn't collide on name.
    base_name = f"{default_label} ({account_email})" if account_email else default_label
    name = base_name
    counter = 1
    while Credential.objects.filter(owner_id=owner_id, name=name, deleted_at__isnull=True).exists():
        name = f"{base_name} ({counter})"
        counter += 1

    return Credential.objects.create(
        owner_id=owner_id,
        type_key=type_key,
        name=name,
        data_encrypted=encrypted,
    )


@extend_schema(tags=["credentials"])
class OAuthStartView(APIView):
    """POST /api/v1/credentials/oauth/<provider>/start/

    Body: { "type_key": "google_email" }
    Returns: { "authorize_url": "https://..." }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, provider: str):
        type_key = request.data.get("type_key", "")
        if not type_key:
            return Response({"detail": "type_key is required"}, status=status.HTTP_400_BAD_REQUEST)

        type_info = get_type(type_key)
        if type_info is None:
            return Response({"detail": f"Unknown type_key: {type_key}"}, status=status.HTTP_400_BAD_REQUEST)

        if type_info.get("mode") != "oauth2":
            return Response(
                {"detail": f"type_key '{type_key}' is not an OAuth2 type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if type_info.get("provider") != provider:
            return Response(
                {"detail": f"type_key '{type_key}' does not belong to provider '{provider}'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider_cfg = get_provider(provider)
        if provider_cfg is None:
            return Response({"detail": f"Unknown provider: {provider}"}, status=status.HTTP_404_NOT_FOUND)

        state = make_state(request.user.pk, type_key)
        scopes = type_info.get("scopes", [])
        redirect_uri = CALLBACK_URL.format(provider=provider)

        params = {
            "client_id": provider_cfg["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
        }
        params.update(provider_cfg.get("extra_authorize_params", {}))

        authorize_url = provider_cfg["authorize_url"] + "?" + urlencode(params)
        return Response({"authorize_url": authorize_url}, status=status.HTTP_200_OK)


@extend_schema(tags=["credentials"])
class OAuthCallbackView(APIView):
    """GET /api/v1/credentials/oauth/<provider>/callback/?code=&state=

    AllowAny — Google redirects the browser here.
    Returns tiny HTML that postMessages to window.opener.
    """

    permission_classes = [AllowAny]

    def get(self, request, provider: str):
        code = request.query_params.get("code", "")
        state = request.query_params.get("state", "")
        error_param = request.query_params.get("error", "")

        if error_param:
            return _error_html(provider, f"Provider returned error: {error_param}")

        if not code or not state:
            return _error_html(provider, "Missing code or state parameter")

        # Verify state
        try:
            state_data = verify_state(state)
        except signing.SignatureExpired:
            return _error_html(provider, "State token expired — please try connecting again")
        except signing.BadSignature:
            return _error_html(provider, "Invalid state token")

        user_id = state_data["user_id"]
        type_key = state_data["type_key"]

        # Validate type + provider still valid
        type_info = get_type(type_key)
        if type_info is None or type_info.get("provider") != provider:
            return _error_html(provider, f"Invalid type_key for provider {provider}")

        provider_cfg = get_provider(provider)
        if provider_cfg is None:
            return _error_html(provider, f"Unknown provider: {provider}")

        # Exchange code for tokens
        try:
            token_resp = exchange_code(provider_cfg, provider, code)
        except Exception as exc:
            return _error_html(provider, f"Token exchange failed: {exc}")

        access_token = token_resp.get("access_token", "")

        # Fetch userinfo (best-effort)
        userinfo: dict = {}
        if access_token and provider_cfg.get("userinfo_url"):
            try:
                userinfo = fetch_userinfo(provider_cfg, access_token)
            except Exception:
                pass

        token_data = build_token_data(token_resp, userinfo)

        # UPSERT credential
        try:
            _upsert_credential(user_id, type_key, token_data)
        except Exception as exc:
            return _error_html(provider, f"Failed to save credential: {exc}")

        body = _SUCCESS_HTML.format(provider=provider, panel_url=_PANEL_URL)
        return HttpResponse(body, content_type="text/html; charset=utf-8")
