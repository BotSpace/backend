# type: ignore
"""Internal endpoints for the agent's RAG indexer.

Returns templates WITH their flow JSON so the agent can embed each one,
index it in pgvector, and reuse the flow when the user asks to build a
matching bot. Public template endpoints intentionally hide `flow`
(payload size and IP protection); these endpoints are gated by the
shared X-Internal-Token used elsewhere (subscription.report_usage).
"""

from django.conf import settings
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.apps.template.models import TemplateModel


def _internal_token_ok(request) -> bool:
    expected = getattr(settings, "INTERNAL_API_TOKEN", None)
    if not expected:
        return False
    provided = request.headers.get("X-Internal-Token", "")
    return provided == expected


def _serialize_template(t: TemplateModel) -> dict:
    # Flow is stored on the linked ProjectModel, not on TemplateModel directly
    project_flow = {}
    if t.project_id and t.project:
        raw = t.project.flow or []
        if isinstance(raw, dict):
            project_flow = raw
        elif isinstance(raw, list):
            # Older format: list of node dicts stored flat
            project_flow = {"nodes": raw, "edges": []}
    flow = project_flow or {"nodes": [], "edges": []}
    return {
        "id": t.id,
        "slug": t.slug,
        "name": t.name,
        "short_description": t.short_description,
        "description": t.description,
        "categories": [{"id": c.id, "name": c.name} for c in t.categories.all()],
        "features": [{"id": f.id, "name": f.name, "value": f.value} for f in t.features.all()],
        "flow": flow,
        "is_verify": t.is_verify,
    }


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def list_templates_with_flow(request):
    """List ALL verified templates with their flow JSON for RAG indexing.

    Header: X-Internal-Token: <settings.INTERNAL_API_TOKEN>
    Optional query: ?only_verified=true (default true)
    Returns: {"results": [{id, slug, name, short_description, description,
                            categories, features, flow, is_verify}, ...]}
    """
    if not _internal_token_ok(request):
        return Response({"detail": "Ruxsat etilmagan so'rov."}, status=403)

    only_verified = request.query_params.get("only_verified", "true").lower() != "false"
    qs = TemplateModel.objects.select_related("project").prefetch_related("categories", "features")
    if only_verified:
        qs = qs.filter(is_verify=True)
    return Response({"results": [_serialize_template(t) for t in qs]})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_template_with_flow(request, identifier):
    """Get a single template (by id or slug) WITH flow JSON.

    Header: X-Internal-Token: <settings.INTERNAL_API_TOKEN>
    """
    if not _internal_token_ok(request):
        return Response({"detail": "Ruxsat etilmagan so'rov."}, status=403)

    qs = TemplateModel.objects.prefetch_related("categories", "features")
    template = qs.filter(id=identifier).first() if identifier.isdigit() else qs.filter(slug=identifier).first()
    if template is None:
        return Response({"detail": "Template topilmadi."}, status=404)
    return Response(_serialize_template(template))
