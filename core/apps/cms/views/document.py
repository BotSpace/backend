"""Document CRUD — MongoDB-backed.

URL pattern:
  /api/v1/cms/projects/<project_id>/collections/<name>/documents/         (GET list, POST create)
  /api/v1/cms/projects/<project_id>/collections/<name>/documents/<id>/    (GET, PATCH, DELETE)
  /api/v1/cms/projects/<project_id>/collections/<name>/documents/bulk/    (POST bulk_insert)
  /api/v1/cms/projects/<project_id>/collections/<name>/documents/aggregate/  (POST)
  /api/v1/cms/projects/<project_id>/collections/<name>/documents/<id>/restore/ (POST)
"""

from __future__ import annotations

from bson.errors import BSONError
from drf_spectacular.utils import extend_schema
from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.apps.cms.services import documents as doc_svc
from core.apps.cms.services import mongo
from core.apps.cms.services.validator import ValidationError

from ._common import get_collection_or_404


@extend_schema(tags=["cms"])
class DocumentViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, project_id=None, collection_name=None):
        coll = get_collection_or_404(project_id=project_id, name=collection_name)
        try:
            limit = max(1, min(int(request.query_params.get("limit") or 50), 500))
            skip = max(0, int(request.query_params.get("skip") or 0))
        except ValueError:
            return Response({"detail": "invalid limit/skip"}, status=400)
        sort = []
        if request.query_params.get("sort"):
            for part in request.query_params["sort"].split(","):
                part = part.strip()
                if not part:
                    continue
                if part.startswith("-"):
                    sort.append((part[1:], -1))
                else:
                    sort.append((part, 1))
        import json as _json
        try:
            filter_raw = request.query_params.get("filter")
            filter = _json.loads(filter_raw) if filter_raw else {}
        except _json.JSONDecodeError:
            return Response({"detail": "filter must be JSON"}, status=400)
        items = mongo.find(
            coll.project_id,
            coll.name,
            filter=filter,
            sort=sort or None,
            limit=limit,
            skip=skip,
            include_deleted=request.query_params.get("include_deleted") == "1",
        )
        total = mongo.count(coll.project_id, coll.name, filter)
        return Response({"results": items, "total": total, "limit": limit, "skip": skip})

    def retrieve(self, request, project_id=None, collection_name=None, pk=None):
        coll = get_collection_or_404(project_id=project_id, name=collection_name)
        item = mongo.find_one(coll.project_id, coll.name, {"_id": pk})
        if item is None:
            return Response({"detail": "not found"}, status=404)
        return Response(item)

    def create(self, request, project_id=None, collection_name=None):
        coll = get_collection_or_404(project_id=project_id, name=collection_name)
        try:
            res = doc_svc.insert(coll, request.data, actor_id=request.user.id if request.user.is_authenticated else None)
        except ValidationError as exc:
            return Response({"errors": exc.errors}, status=400)
        except (BSONError, PyMongoError) as exc:
            return Response({"detail": f"storage error: {exc}"}, status=422)
        return Response(res, status=status.HTTP_201_CREATED)

    def partial_update(self, request, project_id=None, collection_name=None, pk=None):
        coll = get_collection_or_404(project_id=project_id, name=collection_name)
        expected_version = request.data.pop("_version", None) if isinstance(request.data, dict) else None
        try:
            res = doc_svc.update(
                coll,
                document_id=pk,
                patch=request.data,
                expected_version=int(expected_version) if expected_version is not None else None,
                actor_id=request.user.id if request.user.is_authenticated else None,
            )
        except ValidationError as exc:
            return Response({"errors": exc.errors}, status=400)
        except LookupError as exc:
            return Response({"detail": str(exc)}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        except (BSONError, PyMongoError) as exc:
            return Response({"detail": f"storage error: {exc}"}, status=422)
        return Response(res)

    def destroy(self, request, project_id=None, collection_name=None, pk=None):
        coll = get_collection_or_404(project_id=project_id, name=collection_name)
        ok = doc_svc.soft_delete(
            coll,
            document_id=pk,
            actor_id=request.user.id if request.user.is_authenticated else None,
        )
        return Response(status=204 if ok else 404)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, project_id=None, collection_name=None, pk=None):
        coll = get_collection_or_404(project_id=project_id, name=collection_name)
        ok = doc_svc.restore(
            coll,
            document_id=pk,
            actor_id=request.user.id if request.user.is_authenticated else None,
        )
        return Response({"restored": ok}, status=200 if ok else 404)

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk_insert(self, request, project_id=None, collection_name=None):
        coll = get_collection_or_404(project_id=project_id, name=collection_name)
        docs = request.data.get("documents") if isinstance(request.data, dict) else request.data
        if not isinstance(docs, list):
            return Response({"detail": "documents must be a list"}, status=400)
        try:
            res = doc_svc.bulk_insert(
                coll,
                docs,
                actor_id=request.user.id if request.user.is_authenticated else None,
            )
        except ValidationError as exc:
            return Response({"errors": exc.errors}, status=400)
        except (BSONError, PyMongoError) as exc:
            return Response({"detail": f"storage error: {exc}"}, status=422)
        return Response(res, status=201)

    @action(detail=False, methods=["post"], url_path="aggregate")
    def aggregate(self, request, project_id=None, collection_name=None):
        coll = get_collection_or_404(project_id=project_id, name=collection_name)
        pipeline = request.data.get("pipeline") if isinstance(request.data, dict) else None
        if not isinstance(pipeline, list):
            return Response({"detail": "pipeline must be a list"}, status=400)
        limit = int(request.data.get("limit") or 500) if isinstance(request.data, dict) else 500
        rows = mongo.aggregate(coll.project_id, coll.name, pipeline, limit=limit)
        return Response({"results": rows, "count": len(rows)})

    @action(detail=False, methods=["get"], url_path="count")
    def count(self, request, project_id=None, collection_name=None):
        coll = get_collection_or_404(project_id=project_id, name=collection_name)
        import json as _json
        try:
            filter_raw = request.query_params.get("filter")
            filter = _json.loads(filter_raw) if filter_raw else {}
        except _json.JSONDecodeError:
            return Response({"detail": "filter must be JSON"}, status=400)
        return Response({"count": mongo.count(coll.project_id, coll.name, filter)})
