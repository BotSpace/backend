"""Biznes-darajadagi Prometheus metrikalar.

django_prometheus `/metrics/` endpoint orqali Prometheus tomonidan o'qiladi
(ServiceMonitor: `web`). Web server 4 ta gunicorn worker'da ishlaydi va
``PROMETHEUS_MULTIPROC_DIR`` o'rnatilgan — shuning uchun faqat **Counter**
(va Histogram) ishlatamiz: ular multiprocess-rejimda har worker o'z faylga
yozadi va scrape paytida yig'iladi. Gauge multiprocess'da chalkash bo'lgani
uchun ishlatmaymiz — "vaqt bo'yicha aktivlik" Grafana'da counter'lar ustidan
``rate()`` bilan chiqariladi.

Hamma increment'lar ``safe_inc`` orqali — metrika xatosi hech qachon asosiy
so'rov oqimini buzmasligi kerak.
"""

from __future__ import annotations

import logging

from prometheus_client import Counter

logger = logging.getLogger(__name__)


# Yangi ro'yxatdan o'tishlar — rate() bilan "qaysi vaqtda ko'p" ko'rinadi.
USER_REGISTRATIONS = Counter(
    "botspace_user_registrations_total",
    "Yangi ro'yxatdan o'tgan foydalanuvchilar soni.",
)

# Muvaffaqiyatli login'lar — aktiv foydalanuvchilarning vaqt taqsimoti uchun.
USER_LOGINS = Counter(
    "botspace_user_logins_total",
    "Muvaffaqiyatli login (autentifikatsiya) soni.",
    ["method"],  # telegram | jwt
)

# AI agent ishga tushishi (backend token-hisobotini olganda = bitta run).
AI_RUNS = Counter(
    "botspace_ai_runs_total",
    "AI agent run'lari (token hisobot kelganda hisoblanadi).",
)

# AI sarflagan tokenlar (kirish/chiqish) — AI'dan foydalanishning vaqt grafigi.
AI_TOKENS = Counter(
    "botspace_ai_tokens_total",
    "AI tomonidan sarflangan tokenlar soni.",
    ["kind"],  # input | output
)


def safe_inc(metric: Counter, amount: float = 1, **labels: str) -> None:
    """Counter'ni xavfsiz oshiradi — istisno bo'lsa ham so'rovni buzmaydi."""
    if amount <= 0:
        return
    try:
        target = metric.labels(**labels) if labels else metric
        target.inc(amount)
    except Exception:  # noqa: BLE001
        logger.debug("prometheus metric inc failed", exc_info=True)
