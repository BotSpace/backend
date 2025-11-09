import logging

from celery import shared_task

from core.apps.api.models.message import MessageModel
from core.apps.cms.models import CollectionModel
from core.apps.cms.services import find, get_collection_name


@shared_task
def send_message(message_id: int):
    try:
        message = MessageModel.objects.get(id=message_id)
    except MessageModel.DoesNotExist:
        logging.error("Message does not exist")
        return
    try:
        collection = CollectionModel.objects.get(project=message.project, name="users")
    except CollectionModel.DoesNotExist:
        logging.error("Collection does not exist")
        return
    users: dict = find(get_collection_name(collection))
    done: int = 0
    fail: int = 0
    for user in users:
        chat_id = user.get("chat_id")
        if chat_id is None:
            fail += 1
            continue
        print("xabar yuborildi %s %s" % (chat_id, message.caption))
        done += 1
    message.done = done
    message.fail = fail
    message.save()
    logging.info("Message sent successfully")
    logging.info("Message id: {}".format(message.pk))