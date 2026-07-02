"""Yengil fire-and-forget background ijro (celery o'rniga, thread bilan).

Celery'dan Go worker'ga migratsiyada og'ir/tez-tez ishlaydigan tasklar
worker-golang'ga ko'chdi (Redis Stream). Qolgan KAM CHAQIRILADIGAN va Django
logikasiga chuqur bog'liq ishlar (SMS yuborish, default modullarni yoqish,
legacy Excel export) uchun alohida queue ortiqcha — daemon thread yetadi.

Cheklov: web pod o'chsa thread ham o'ladi (best-effort). Bu tasklar uchun
qabul qilinarli: SMS ~1s, modul yoqish bir necha soniya, export kamdan-kam.
"""

import logging
import threading

logger = logging.getLogger(__name__)


def run(fn, *args, **kwargs) -> None:
    """fn(*args, **kwargs)'ni daemon thread'da ishga tushiradi (xatoni log qiladi)."""

    def _target():
        try:
            fn(*args, **kwargs)
        except Exception:  # noqa: BLE001 — background ish request'ni yiqitmasin
            logger.exception("background task failed: %s", getattr(fn, "__name__", fn))

    threading.Thread(target=_target, daemon=True, name=f"bg-{getattr(fn, '__name__', 'task')}").start()
