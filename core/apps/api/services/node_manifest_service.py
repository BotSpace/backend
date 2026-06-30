"""Unified node manifest — built-in + modul manifestlarini birlashtiradi.

Yagona manba: backend. Built-in node manifestlari shu repo'dagi
`data/builtin_node_manifests.json` da (AI docs bilan); modul node manifestlari
modullarning `describe()` RPC'sidan keladi (module_service). Constructor, agent
va boshqalar shu birlashgan manifestni `/project/{id}/node-manifests/` orqali oladi.
"""

import json
from functools import lru_cache
from pathlib import Path

from .module_service import get_project_module_manifests

_BUILTIN_PATH = Path(__file__).resolve().parent.parent / "data" / "builtin_node_manifests.json"


@lru_cache(maxsize=1)
def get_builtin_node_manifests() -> list:
    """Built-in node manifestlari (kanonik, AI docs bilan). Bir marta o'qib keshlanadi."""
    return json.loads(_BUILTIN_PATH.read_text(encoding="utf-8"))


def get_unified_node_manifests(project) -> list:
    """Built-in + project'ning enabled modul node manifestlari (bitta flat array).

    Built-in node'lar global; modul node'lar per-project (`moduleSlug`/`moduleName`
    bilan teglangan). Type bo'yicha to'qnashuvda built-in ustun (modul built-in
    type'ni qayta belgilay olmaydi).
    """
    builtin = [dict(n) for n in get_builtin_node_manifests()]
    seen = {n.get("type") for n in builtin}
    modules = [n for n in get_project_module_manifests(project) if n.get("type") not in seen]
    return builtin + modules
