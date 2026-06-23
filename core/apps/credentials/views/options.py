"""POST /api/v1/credentials/options/<resource>/ — dynamic options endpoint."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.credentials.models import Credential
from core.apps.credentials.registry import get_type
from core.apps.credentials.services import crypto
from core.apps.credentials.services.oauth import get_valid_access_token
from core.apps.credentials.services.options import OPTION_LOADERS, load_module_options


@extend_schema(tags=["credentials"])
class CredentialOptionsView(APIView):
    """Load dynamic options for a credential resource.

    Returns {"options": [...]} on success or {"options": [], "error": "..."} on failure.
    Never returns 500 for upstream (Google/API/module) errors.

    Request body:
        credential_id  (int|null, optional for module path)
        params         (dict, optional)
        module_slug    (str, optional) — used when credential_id is absent for module path

    Resolution order:
    1. OPTION_LOADERS (built-in Google loaders) — matched by resource name.
       credential_id is required for built-in loaders.
    2. Module fallback — slug derived from credential type_key prefix OR module_slug param;
       options.load RPC is called on that module's endpoint.
       credential_id is optional: if provided, decrypted data is forwarded; otherwise
       credentials: {} is sent.
    3. 400 only when credential_id is missing for a built-in loader.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, resource: str):
        credential_id = request.data.get("credential_id")
        module_slug = request.data.get("module_slug") or ""
        params = request.data.get("params") or {}

        loader = OPTION_LOADERS.get(resource)

        # --- Built-in loader path (Google Sheets / Drive) ---
        if loader is not None:
            if not credential_id:
                return Response({"detail": "credential_id is required"}, status=400)

            cred = Credential.objects.filter(
                owner=request.user,
                id=credential_id,
                deleted_at__isnull=True,
            ).first()
            if cred is None:
                return Response({"detail": "Credential not found"}, status=404)

            try:
                token = _resolve_token(cred)
            except Exception as exc:
                return Response({"options": [], "error": str(exc)})

            try:
                options = loader(token, params)
            except Exception as exc:
                return Response({"options": [], "error": str(exc)})

            return Response({"options": options})

        # --- Module fallback path (credential optional) ---
        cred = None
        if credential_id:
            cred = Credential.objects.filter(
                owner=request.user,
                id=credential_id,
                deleted_at__isnull=True,
            ).first()
            if cred is None:
                return Response({"detail": "Credential not found"}, status=404)

        decrypted: dict | None = None
        if cred is not None:
            try:
                decrypted = crypto.decrypt(cred.data_encrypted)
            except Exception as exc:
                return Response({"options": [], "error": f"Credential decrypt failed: {exc}"})

        try:
            options = load_module_options(
                resource=resource,
                params=params,
                cred_type_key=cred.type_key if cred else None,
                decrypted_data=decrypted,
                module_slug=module_slug or None,
            )
        except Exception as exc:
            return Response({"options": [], "error": str(exc)})

        return Response({"options": options})


def _resolve_token(cred: Credential) -> str:
    """Return a usable token for the credential.

    oauth2 types: use get_valid_access_token (auto-refresh).
    Others: decrypt data_encrypted and use api_key field.
    """
    type_info = get_type(cred.type_key)
    if type_info and type_info.get("mode") == "oauth2":
        return get_valid_access_token(cred)
    # Non-oauth: decrypt and fall back to api_key
    data = crypto.decrypt(cred.data_encrypted)
    api_key = data.get("api_key") or data.get("token") or ""
    return api_key
