import logging
from celery import shared_task

from core.apps.api.models.project import ProjectModel


@shared_task
def proccess_payment():
    for project in ProjectModel.objects.all():
        try:
            pass
            # uresource = project_uresources(project, time=timedelta(hours=1))
            # storage = get_project_storage(project)
            # ram = uresource.get("total_ram") or 0
            # cpu = uresource.get("total_cpu") or 0
            # net_tx = uresource.get("total_net_tx") or 0
            # net_rx = uresource.get("total_net_rx") or 0
            # storage = storage or 0
            #
            # ram_price = ram * settings.RAM_PRICE
            # cpu_price = cpu * settings.CPU_PRICE
            # net_tx_price = net_tx * settings.NET_TX_PRICE
            # net_rx_price = net_rx * settings.NET_RX_PRICE
            # storage_price = storage * settings.STORAGE_PRICE
            #
            # total_price = ram_price + cpu_price + net_rx_price + net_tx_price + storage_price
            #
            # histories = [
            #     HistoryModel(type="ram", amount=ram_price, project=project),
            #     HistoryModel(type="cpu", amount=cpu_price, project=project),
            #     HistoryModel(type="net_tx", amount=net_tx_price, project=project),
            #     HistoryModel(type="net_rx", amount=net_rx_price, project=project),
            #     HistoryModel(type="storage", amount=storage_price, project=project),
            # ]
            # HistoryModel.objects.bulk_create(histories)
            # user = project.owner
            # user.balance -= total_price
            # user.save()
        except Exception as err:
            logging.critical("pul yechishda xato err=%s", err)
