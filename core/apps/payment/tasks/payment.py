import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="payment.process_resource_usage")
def process_resource_usage() -> None:
    """Loyiha resurslari bo'yicha hisob-kitob qiluvchi periodik vazifa.

    Hozircha placeholder: resource-pricing logic ishlab chiqilishi kutilmoqda.
    Yoqilganda config/conf/celery.py'dagi beat schedule kommentdan chiqarilsin.
    """
    logger.info("process_resource_usage placeholder invoked")
