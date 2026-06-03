"""OAuth 2.1 Authorization Server views for MCP clients.

Spec: RFC 8414 (metadata), RFC 7591 (DCR), RFC 6749 (token),
      RFC 7636 (PKCE S256), RFC 8707 (resource - accepted, not enforced).

All public-facing endpoints (metadata, register, token) return raw JSON
without the {status, data} envelope so MCP clients (Claude Code etc.)
receive standard OAuth shapes. The approve endpoint uses the envelope
because it is called by our own dashboard.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode, urlparse

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from config.env import env
from core.services.response import error_response
from core.throttle.ip_throttle import IPThrottle

User = get_user_model()

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

_OAUTH_CLIENT_TTL = 90 * 24 * 3600  # 90 days
_AUTH_CODE_TTL = 300  # 5 minutes


def _issuer() -> str:
    return env.str("OAUTH_ISSUER", default="https://api.botspace.uz")


def _authorize_page() -> str:
    return env.str("OAUTH_AUTHORIZE_PAGE", default="https://botspace.uz/oauth/authorize")


def _oauth_error(error: str, description: str = "", http_status: int = 400) -> Response:
    """Return a raw RFC 6749 error response (no envelope)."""
    body: dict = {"error": error}
    if description:
        body["error_description"] = description
    return Response(body, status=http_status)


def _validate_redirect_uri(uri: str) -> str | None:
    """Return None if valid, else an error message string."""
    try:
        parsed = urlparse(uri)
    except Exception:
        return "Invalid URI"
    if parsed.scheme not in ("http", "https"):
        return f"redirect_uri scheme must be http or https, got: {parsed.scheme!r}"
    if parsed.scheme == "http":
        host = parsed.hostname or ""
        if host not in ("localhost", "127.0.0.1"):
            return "http redirect_uri is only allowed for localhost / 127.0.0.1"
    return None


def _verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return computed == code_challenge


def _access_token_lifetime_seconds() -> int:
    from django.conf import settings

    lifetime = settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME")
    if lifetime is None:
        return 900
    return int(lifetime.total_seconds())


# --------------------------------------------------------------------------- #
# 1. Metadata  GET /.well-known/oauth-authorization-server
# --------------------------------------------------------------------------- #

class OAuthMetadataView(APIView):
    """RFC 8414 Authorization Server Metadata — raw JSON, no envelope."""
    permission_classes = [AllowAny]
    authentication_classes = []  # no auth parsing needed

    def get(self, request: Request) -> Response:
        issuer = _issuer()
        data = {
            "issuer": issuer,
            "authorization_endpoint": _authorize_page(),
            "token_endpoint": f"{issuer}/auth/oauth/token/",
            "registration_endpoint": f"{issuer}/auth/oauth/register/",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": ["mcp"],
        }
        return Response(data, status=status.HTTP_200_OK)


# --------------------------------------------------------------------------- #
# 2. DCR  POST /auth/oauth/register/
# --------------------------------------------------------------------------- #

class OAuthRegisterView(APIView):
    """RFC 7591 Dynamic Client Registration — raw JSON 201, no envelope."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [IPThrottle]

    def post(self, request: Request) -> Response:
        redirect_uris = request.data.get("redirect_uris")
        client_name = (request.data.get("client_name") or "").strip() or "MCP Client"

        if not redirect_uris or not isinstance(redirect_uris, list):
            return _oauth_error("invalid_client_metadata", "redirect_uris must be a non-empty list")

        for uri in redirect_uris:
            err = _validate_redirect_uri(uri)
            if err:
                return _oauth_error("invalid_redirect_uri", err)

        client_id = secrets.token_urlsafe(24)
        client_data = {
            "redirect_uris": redirect_uris,
            "client_name": client_name,
        }
        cache.set(f"oauth:client:{client_id}", client_data, timeout=_OAUTH_CLIENT_TTL)

        return Response(
            {
                "client_id": client_id,
                "client_id_issued_at": int(time.time()),
                "redirect_uris": redirect_uris,
                "client_name": client_name,
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
            },
            status=status.HTTP_201_CREATED,
        )


# --------------------------------------------------------------------------- #
# 3. Authorize meta  GET /auth/oauth/authorize/meta/
# --------------------------------------------------------------------------- #

class OAuthAuthorizeMetaView(APIView):
    """Validate authorize params for the dashboard consent page.

    Returns envelope-wrapped response because it is called by our dashboard.
    On success: {"status": true, "data": {"client_name": ..., "redirect_uri": ...}}
    On error: 400 with plain message (envelope via error_response).
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request: Request) -> Response:
        params = request.query_params
        client_id = params.get("client_id", "").strip()
        redirect_uri = params.get("redirect_uri", "").strip()
        response_type = params.get("response_type", "").strip()
        code_challenge = params.get("code_challenge", "").strip()
        code_challenge_method = params.get("code_challenge_method", "").strip()

        if not client_id:
            return error_response({"detail": "client_id is required"}, 400)
        if response_type != "code":
            return error_response({"detail": "response_type must be 'code'"}, 400)
        if not code_challenge:
            return error_response({"detail": "code_challenge is required"}, 400)
        if code_challenge_method != "S256":
            return error_response({"detail": "code_challenge_method must be S256"}, 400)
        if not redirect_uri:
            return error_response({"detail": "redirect_uri is required"}, 400)

        client = cache.get(f"oauth:client:{client_id}")
        if client is None:
            return error_response({"detail": "Unknown client_id"}, 400)
        if redirect_uri not in client["redirect_uris"]:
            return error_response({"detail": "redirect_uri does not match registered URIs"}, 400)

        from core.services.response import success_response
        return success_response({"client_name": client["client_name"], "redirect_uri": redirect_uri})


# --------------------------------------------------------------------------- #
# 4. Approve  POST /auth/oauth/authorize/approve/
# --------------------------------------------------------------------------- #

class OAuthAuthorizeApproveView(APIView):
    """Issue auth code after user consents — requires valid JWT.

    Returns envelope-wrapped response (called by our dashboard).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        data = request.data
        client_id = (data.get("client_id") or "").strip()
        redirect_uri = (data.get("redirect_uri") or "").strip()
        response_type = (data.get("response_type") or "").strip()
        code_challenge = (data.get("code_challenge") or "").strip()
        code_challenge_method = (data.get("code_challenge_method") or "").strip()
        state = (data.get("state") or "").strip()
        scope = (data.get("scope") or "mcp").strip()
        resource = (data.get("resource") or "").strip()

        if not client_id:
            return error_response({"detail": "client_id is required"}, 400)
        if response_type != "code":
            return error_response({"detail": "response_type must be 'code'"}, 400)
        if not code_challenge:
            return error_response({"detail": "code_challenge is required"}, 400)
        if code_challenge_method != "S256":
            return error_response({"detail": "code_challenge_method must be S256"}, 400)
        if not redirect_uri:
            return error_response({"detail": "redirect_uri is required"}, 400)

        client = cache.get(f"oauth:client:{client_id}")
        if client is None:
            return error_response({"detail": "Unknown client_id"}, 400)
        if redirect_uri not in client["redirect_uris"]:
            return error_response({"detail": "redirect_uri does not match registered URIs"}, 400)

        code = secrets.token_urlsafe(32)
        cache.set(
            f"oauth:code:{code}",
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": code_challenge,
                "user_id": request.user.id,
                "scope": scope,
                "resource": resource,
            },
            timeout=_AUTH_CODE_TTL,
        )

        qs: dict = {"code": code}
        if state:
            qs["state"] = state
        redirect_url = redirect_uri + ("?" if "?" not in redirect_uri else "&") + urlencode(qs)

        from core.services.response import success_response
        return success_response({"redirect_url": redirect_url})


# --------------------------------------------------------------------------- #
# 5. Token  POST /auth/oauth/token/
# --------------------------------------------------------------------------- #

class OAuthTokenView(APIView):
    """RFC 6749 token endpoint — raw JSON, no envelope.

    Accepts both application/x-www-form-urlencoded and application/json.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def _get_param(self, request: Request, key: str) -> str:
        # request.data works for both form-encoded and JSON
        return (request.data.get(key) or "").strip()

    def post(self, request: Request) -> Response:
        grant_type = self._get_param(request, "grant_type")

        if grant_type == "authorization_code":
            return self._handle_authorization_code(request)
        if grant_type == "refresh_token":
            return self._handle_refresh_token(request)
        return _oauth_error("unsupported_grant_type", f"grant_type {grant_type!r} is not supported")

    def _handle_authorization_code(self, request: Request) -> Response:
        code = self._get_param(request, "code")
        code_verifier = self._get_param(request, "code_verifier")
        client_id = self._get_param(request, "client_id")
        redirect_uri = self._get_param(request, "redirect_uri")

        if not code:
            return _oauth_error("invalid_request", "code is required")
        if not code_verifier:
            return _oauth_error("invalid_request", "code_verifier is required")
        if not client_id:
            return _oauth_error("invalid_request", "client_id is required")
        if not redirect_uri:
            return _oauth_error("invalid_request", "redirect_uri is required")

        cache_key = f"oauth:code:{code}"
        code_data = cache.get(cache_key)
        # Delete immediately — one-time use
        cache.delete(cache_key)

        if code_data is None:
            return _oauth_error("invalid_grant", "Authorization code is invalid or expired")
        if code_data["client_id"] != client_id:
            return _oauth_error("invalid_grant", "client_id mismatch")
        if code_data["redirect_uri"] != redirect_uri:
            return _oauth_error("invalid_grant", "redirect_uri mismatch")

        if not _verify_pkce(code_verifier, code_data["code_challenge"]):
            return _oauth_error("invalid_grant", "PKCE code_verifier verification failed")

        try:
            user = User.objects.get(pk=code_data["user_id"])
        except User.DoesNotExist:
            return _oauth_error("invalid_grant", "User not found")

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access_token": str(refresh.access_token),
                "token_type": "Bearer",
                "expires_in": _access_token_lifetime_seconds(),
                "refresh_token": str(refresh),
                "scope": code_data.get("scope", "mcp"),
            },
            status=status.HTTP_200_OK,
        )

    def _handle_refresh_token(self, request: Request) -> Response:
        raw_refresh = self._get_param(request, "refresh_token")
        if not raw_refresh:
            return _oauth_error("invalid_request", "refresh_token is required")

        serializer = TokenRefreshSerializer(data={"refresh": raw_refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            return _oauth_error("invalid_grant", str(exc))
        except Exception:
            return _oauth_error("invalid_grant", "Invalid or expired refresh token")

        validated = serializer.validated_data
        body: dict = {
            "access_token": validated["access"],
            "token_type": "Bearer",
            "expires_in": _access_token_lifetime_seconds(),
        }
        # ROTATE_REFRESH_TOKENS=True means a new refresh token is returned
        if "refresh" in validated:
            body["refresh_token"] = validated["refresh"]

        return Response(body, status=status.HTTP_200_OK)
