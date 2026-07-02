# type: ignore
"""
SMS tasdiqlash kodi yuborish.

send_confirm_sms — plain funksiya: core/services/sms.py uni background thread'da
chaqiradi (celery'siz ishlaydi). SendConfirm celery task'i eski queue'da qolib
ketgan xabarlar uchun backward-compat sifatida saqlangan.
"""

import logging
import os
from importlib import import_module

from celery import shared_task
from config.env import env
from django.utils.translation import gettext as _


def send_confirm_sms(phone, code):
    """Tasdiqlash ko'dini yuborish

    Args:
        phone (str, int): telefon no'mer
        code (str, int): tasdiqlash ko'di
    """
    try:
        service = getattr(
            import_module(os.getenv("OTP_MODULE")), os.getenv("OTP_SERVICE")
        )()
        service.send_sms(
            phone, env.str("OTP_MESSAGE", _("Sizning Tasdiqlash ko'dingiz: %(code)s")) % {"code": code}
        )
        logging.info("Sms send: %s-%s" % (phone, code))
    except Exception as e:
        logging.error(
            "Error: {phone}-{code}\n\n{error}".format(phone=phone, code=code, error=e)
        )  # noqa
        raise Exception


@shared_task
def SendConfirm(phone, code):
    """Backward-compat celery task (eski queue'dagi xabarlar uchun)."""
    send_confirm_sms(phone, code)
